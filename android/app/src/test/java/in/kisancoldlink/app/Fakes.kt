package `in`.kisancoldlink.app

import `in`.kisancoldlink.app.audio.AudioPlayer
import `in`.kisancoldlink.app.audio.PlaybackState
import `in`.kisancoldlink.app.core.networking.AppError
import `in`.kisancoldlink.app.data.dto.LotViewDto
import `in`.kisancoldlink.app.domain.model.Advisory
import `in`.kisancoldlink.app.domain.model.AdvisoryStage
import `in`.kisancoldlink.app.domain.model.AppLanguage
import `in`.kisancoldlink.app.domain.model.LivePrice
import `in`.kisancoldlink.app.domain.model.LotDetailResult
import `in`.kisancoldlink.app.domain.model.LotSession
import `in`.kisancoldlink.app.domain.repository.AdvisoryRepository
import `in`.kisancoldlink.app.domain.repository.LotRepository
import `in`.kisancoldlink.app.domain.repository.ReminderSettings
import `in`.kisancoldlink.app.domain.repository.SessionRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.serialization.json.Json
import java.io.File

/** Test doubles. Lot data comes from fixtures recorded from the real backend (see resources/fixtures/README.txt). */
object Fixtures {
    val json = Json { ignoreUnknownKeys = true; explicitNulls = false }
    fun text(name: String): String = javaClass.classLoader!!.getResource("fixtures/$name.json")!!.readText()
    fun lotView(): LotViewDto = json.decodeFromString(
        `in`.kisancoldlink.app.data.dto.EnvelopeDto.serializer(LotViewDto.serializer()), text("lot_view")).data
    val session = LotSession("lot1", "token", "Paddy (Dhan)(Common)", "వరి", "Paddy")
}

class FakeSessions(language: AppLanguage = AppLanguage.TELUGU, session: LotSession? = Fixtures.session) : SessionRepository {
    override val language = MutableStateFlow(language)
    override val onboarded = MutableStateFlow(true)
    override val session = MutableStateFlow(session)
    override val reminder = MutableStateFlow(ReminderSettings())
    override suspend fun setLanguage(language: AppLanguage) { this.language.value = language }
    override suspend fun setOnboarded() { onboarded.value = true }
    override suspend fun saveSession(session: LotSession) { this.session.value = session }
    override suspend fun clearSession() { session.value = null }
    override suspend fun setReminder(settings: ReminderSettings) { reminder.value = settings }
}

class FakeLots(var fail: AppError? = null) : LotRepository {
    var calls = 0
    override suspend fun lotDetail(session: LotSession, forceRefresh: Boolean): Result<LotDetailResult> {
        calls++
        return fail?.let { Result.failure(it) } ?: Result.success(LotDetailResult(Fixtures.lotView().toDomain(), false, 0))
    }
    override suspend fun livePrice(session: LotSession, mandi: String): Result<LivePrice?> = Result.success(null)
}

class FakeAdvisories(private val withAudio: Boolean = true) : AdvisoryRepository {
    val requested = mutableListOf<Pair<AdvisoryStage, AppLanguage>>()
    var failStage: AdvisoryStage? = null
    var saved: Advisory? = null
    override suspend fun prepare(session: LotSession, stage: AdvisoryStage, language: AppLanguage): Result<Advisory> {
        requested += stage to language
        if (stage == failStage) return Result.failure(AppError.Network("offline"))
        val script = scriptFor(stage, language, session)
        return Result.success(Advisory(stage, language, script, if (withAudio) File("$stage.mp3") else null,
            if (withAudio) null else "Azure Speech is not configured", aiNarrated = false))
    }
    override suspend fun lastReport(session: LotSession, language: AppLanguage): Advisory? = saved

    companion object {
        fun scriptFor(stage: AdvisoryStage, language: AppLanguage, s: LotSession) = when (stage) {
            AdvisoryStage.GREETING -> if (language == AppLanguage.TELUGU) "బాబాయ్... శుభోదయం! మీ ${s.cropTe} పంట" else "Good morning, Babai! your ${s.cropEn}"
            AdvisoryStage.REPORT -> "report-$language"
            AdvisoryStage.GOODBYE -> if (language == AppLanguage.TELUGU) "సరే బాబాయ్! ధన్యవాదాలు." else "Alright Babai, thank you!"
        }
    }
}

/** Player whose playback the test finishes explicitly, like ExoPlayer reaching STATE_ENDED. */
class FakePlayer : AudioPlayer {
    private val _state = MutableStateFlow<PlaybackState>(PlaybackState.Idle)
    override val state: StateFlow<PlaybackState> = _state
    val played = mutableListOf<String>()
    private var completions = 0
    override fun play(file: File) { played += file.name; _state.value = PlaybackState.Playing(0, 10_000) }
    override fun pause() { (_state.value as? PlaybackState.Playing)?.let { _state.value = PlaybackState.Paused(it.positionMs, it.durationMs) } }
    override fun resume() { (_state.value as? PlaybackState.Paused)?.let { _state.value = PlaybackState.Playing(it.positionMs, it.durationMs) } }
    override fun stop() { _state.value = PlaybackState.Idle }
    fun finish() { _state.value = PlaybackState.Completed(++completions) }
    fun fail() { _state.value = PlaybackState.Error("ERROR_CODE_IO_FILE_NOT_FOUND") }
}
