package `in`.kisancoldlink.app.data.local

import android.content.Context
import dagger.hilt.android.qualifiers.ApplicationContext
import `in`.kisancoldlink.app.data.dto.LotViewDto
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import java.io.File
import java.io.InputStream
import javax.inject.Inject
import javax.inject.Singleton

@Serializable
data class CachedLot(val savedAtMillis: Long, val view: LotViewDto)

@Serializable
data class CachedReport(val savedAtMillis: Long, val script: String, val audioKey: String?, val aiNarrated: Boolean)

/** App-private files: last lot view, advisory MP3s and the last report, for offline replay. */
@Singleton
class LocalFiles @Inject constructor(@ApplicationContext context: Context, private val json: Json) {
    private val root = context.filesDir

    private fun dir(name: String) = File(root, name).apply { mkdirs() }

    suspend fun saveLot(lotId: String, view: LotViewDto, now: Long) = withContext(Dispatchers.IO) {
        File(dir("lots"), "$lotId.json").writeText(json.encodeToString(CachedLot.serializer(), CachedLot(now, view)))
    }

    suspend fun loadLot(lotId: String): CachedLot? = withContext(Dispatchers.IO) {
        File(dir("lots"), "$lotId.json").takeIf { it.exists() }?.let {
            runCatching { json.decodeFromString(CachedLot.serializer(), it.readText()) }.getOrNull()
        }
    }

    fun audioFile(key: String): File = File(dir("advisory"), "$key.mp3")

    /** Writes the download to a temp file first so a broken download never looks like a finished MP3. */
    suspend fun saveAudio(key: String, input: InputStream): File = withContext(Dispatchers.IO) {
        val target = audioFile(key)
        val tmp = File(target.parentFile, "$key.part")
        input.use { src -> tmp.outputStream().use { src.copyTo(it) } }
        if (!tmp.renameTo(target)) error("could not save audio")
        target
    }

    suspend fun saveReport(lotId: String, lang: String, report: CachedReport) = withContext(Dispatchers.IO) {
        File(dir("advisory"), "report_${lotId}_$lang.json").writeText(json.encodeToString(CachedReport.serializer(), report))
    }

    suspend fun loadReport(lotId: String, lang: String): CachedReport? = withContext(Dispatchers.IO) {
        File(dir("advisory"), "report_${lotId}_$lang.json").takeIf { it.exists() }?.let {
            runCatching { json.decodeFromString(CachedReport.serializer(), it.readText()) }.getOrNull()
        }
    }

    suspend fun clearAll() = withContext(Dispatchers.IO) {
        listOf("lots", "advisory").forEach { File(root, it).deleteRecursively() }
    }
}
