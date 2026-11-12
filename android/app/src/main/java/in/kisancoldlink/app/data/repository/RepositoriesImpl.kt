package `in`.kisancoldlink.app.data.repository

import `in`.kisancoldlink.app.core.networking.AppError
import `in`.kisancoldlink.app.core.networking.apiCall
import `in`.kisancoldlink.app.data.dto.AdvisoryRequestDto
import `in`.kisancoldlink.app.data.dto.IdentifyRequestDto
import `in`.kisancoldlink.app.data.local.CachedReport
import `in`.kisancoldlink.app.data.local.LocalFiles
import `in`.kisancoldlink.app.data.remote.KisanApi
import `in`.kisancoldlink.app.domain.model.Advisory
import `in`.kisancoldlink.app.domain.model.AdvisoryStage
import `in`.kisancoldlink.app.domain.model.AppLanguage
import `in`.kisancoldlink.app.domain.model.FarmerLot
import `in`.kisancoldlink.app.domain.model.LivePrice
import `in`.kisancoldlink.app.domain.model.LotDetailResult
import `in`.kisancoldlink.app.domain.model.LotSession
import `in`.kisancoldlink.app.domain.repository.AdvisoryRepository
import `in`.kisancoldlink.app.domain.repository.FarmerRepository
import `in`.kisancoldlink.app.domain.repository.LotRepository
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import javax.inject.Inject
import javax.inject.Singleton

class RemoteFarmerRepository @Inject constructor(private val api: KisanApi) : FarmerRepository {
    override suspend fun identify(name: String, phone: String): Result<List<FarmerLot>> =
        apiCall { api.identify(IdentifyRequestDto(name, phone)).data.map { it.toDomain() } }
}

/** Clock is injectable so cache timestamps are testable. */
fun interface Clock {
    fun now(): Long
}

@Singleton
class RemoteLotRepository @Inject constructor(
    private val api: KisanApi,
    private val files: LocalFiles,
    private val clock: Clock,
) : LotRepository {
    private val mutex = Mutex()
    private var memory: Pair<String, LotDetailResult>? = null

    override suspend fun lotDetail(session: LotSession, forceRefresh: Boolean): Result<LotDetailResult> = mutex.withLock {
        val hit = memory
        if (!forceRefresh && hit != null && hit.first == session.lotId && !hit.second.fromCache &&
            clock.now() - hit.second.fetchedAtMillis < MEMORY_TTL_MS
        ) return Result.success(hit.second)

        val remote = apiCall { api.lot(session.lotId, session.token).data }
        remote.fold(
            onSuccess = { dto ->
                val now = clock.now()
                files.saveLot(session.lotId, dto, now)
                LotDetailResult(dto.toDomain(), fromCache = false, fetchedAtMillis = now).also { memory = session.lotId to it }
                    .let { Result.success(it) }
            },
            onFailure = { err ->
                // Only a network failure falls back to the saved copy; a revoked lot must not show stale data.
                val cached = if (err is AppError.Network) files.loadLot(session.lotId) else null
                if (cached != null) Result.success(LotDetailResult(cached.view.toDomain(), fromCache = true, fetchedAtMillis = cached.savedAtMillis))
                else Result.failure(err)
            },
        )
    }

    override suspend fun livePrice(session: LotSession, mandi: String): Result<LivePrice?> =
        apiCall { api.liveMarket(session.lotId, mandi, session.token).data.toDomain() }

    companion object {
        const val MEMORY_TTL_MS = 5 * 60 * 1000L
    }
}

@Singleton
class RemoteAdvisoryRepository @Inject constructor(
    private val api: KisanApi,
    private val files: LocalFiles,
    private val clock: Clock,
) : AdvisoryRepository {

    override suspend fun prepare(session: LotSession, stage: AdvisoryStage, language: AppLanguage): Result<Advisory> =
        apiCall { api.advisory(session.lotId, AdvisoryRequestDto(stage.code, language.code), session.token).data }.map { dto ->
            var problem = dto.ttsError?.let { it.message.ifBlank { it.code } }
            val file = dto.audio?.let { audio ->
                val existing = files.audioFile(audio.key)
                if (existing.exists() && existing.length() > 0) existing
                else apiCall { api.audio(audio.path.trimStart('/'), session.token) }.fold(
                    onSuccess = { body -> runCatching { files.saveAudio(audio.key, body.byteStream()) }.getOrNull() },
                    onFailure = { null },
                ).also { if (it == null) problem = "audio download failed" }
            }
            val advisory = Advisory(stage, language, dto.script, file, problem, dto.narration == "bedrock")
            if (stage == AdvisoryStage.REPORT) {
                files.saveReport(session.lotId, language.code,
                    CachedReport(clock.now(), dto.script, dto.audio?.key?.takeIf { file != null }, advisory.aiNarrated))
            }
            advisory
        }

    override suspend fun lastReport(session: LotSession, language: AppLanguage): Advisory? =
        files.loadReport(session.lotId, language.code)?.let { r ->
            val file = r.audioKey?.let { files.audioFile(it) }?.takeIf { it.exists() }
            Advisory(AdvisoryStage.REPORT, language, r.script, file, if (file == null) "saved audio missing" else null, r.aiNarrated)
        }
}
