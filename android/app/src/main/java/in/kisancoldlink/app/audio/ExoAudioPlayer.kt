package `in`.kisancoldlink.app.audio

import android.content.Context
import android.os.Handler
import android.os.Looper
import androidx.media3.common.AudioAttributes
import androidx.media3.common.C
import androidx.media3.common.MediaItem
import androidx.media3.common.PlaybackException
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.io.File
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Media3 ExoPlayer for local advisory MP3s. Singleton, so it survives activity recreation and
 * recomposition never restarts audio. All calls happen on the main thread (ExoPlayer requirement).
 */
@Singleton
class ExoAudioPlayer @Inject constructor(@ApplicationContext private val context: Context) : AudioPlayer {
    private val main = Handler(Looper.getMainLooper())
    private val _state = MutableStateFlow<PlaybackState>(PlaybackState.Idle)
    override val state: StateFlow<PlaybackState> = _state.asStateFlow()
    private var completions = 0
    private var player: ExoPlayer? = null

    private val ticker = object : Runnable {
        override fun run() {
            val p = player ?: return
            if (p.isPlaying) {
                _state.value = PlaybackState.Playing(p.currentPosition, p.duration.coerceAtLeast(0))
                main.postDelayed(this, 250)
            }
        }
    }

    private fun obtain(): ExoPlayer = player ?: ExoPlayer.Builder(context)
        .setAudioAttributes(
            AudioAttributes.Builder().setContentType(C.AUDIO_CONTENT_TYPE_SPEECH).setUsage(C.USAGE_MEDIA).build(),
            /* handleAudioFocus = */ true,
        )
        .build().also { p ->
            p.addListener(object : Player.Listener {
                override fun onIsPlayingChanged(isPlaying: Boolean) {
                    if (isPlaying) {
                        main.removeCallbacks(ticker)
                        main.post(ticker)
                    } else if (p.playbackState == Player.STATE_READY) {
                        _state.value = PlaybackState.Paused(p.currentPosition, p.duration.coerceAtLeast(0))
                    }
                }

                override fun onPlaybackStateChanged(playbackState: Int) {
                    when (playbackState) {
                        Player.STATE_BUFFERING -> _state.value = PlaybackState.Loading
                        Player.STATE_ENDED -> {
                            main.removeCallbacks(ticker)
                            _state.value = PlaybackState.Completed(++completions)
                        }
                        else -> Unit
                    }
                }

                override fun onPlayerError(error: PlaybackException) {
                    main.removeCallbacks(ticker)
                    _state.value = PlaybackState.Error(error.errorCodeName)
                }
            })
            player = p
        }

    override fun play(file: File) {
        val p = obtain()
        p.stop()
        p.clearMediaItems()
        _state.value = PlaybackState.Loading
        p.setMediaItem(MediaItem.fromUri(android.net.Uri.fromFile(file)))
        p.prepare()
        p.play()
    }

    override fun pause() {
        player?.pause()
    }

    override fun resume() {
        player?.play()
    }

    override fun stop() {
        main.removeCallbacks(ticker)
        player?.stop()
        _state.value = PlaybackState.Idle
    }
}
