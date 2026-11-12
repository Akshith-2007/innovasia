package `in`.kisancoldlink.app.audio

import kotlinx.coroutines.flow.StateFlow
import java.io.File

/** Real playback state; the call screen only shows "speaking" while this says Playing. */
sealed interface PlaybackState {
    data object Idle : PlaybackState
    data object Loading : PlaybackState
    data class Playing(val positionMs: Long, val durationMs: Long) : PlaybackState
    data class Paused(val positionMs: Long, val durationMs: Long) : PlaybackState
    /** [id] grows with every finished playback so two completions in a row are distinct StateFlow values. */
    data class Completed(val id: Int) : PlaybackState
    data class Error(val message: String) : PlaybackState
}

interface AudioPlayer {
    val state: StateFlow<PlaybackState>
    fun play(file: File)
    fun pause()
    fun resume()
    fun stop()
}
