package `in`.kisancoldlink.app.features.call

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import `in`.kisancoldlink.app.audio.AudioPlayer
import `in`.kisancoldlink.app.audio.PlaybackState
import `in`.kisancoldlink.app.core.networking.AppError
import `in`.kisancoldlink.app.domain.model.Advisory
import `in`.kisancoldlink.app.domain.model.AdvisoryStage
import `in`.kisancoldlink.app.domain.model.AppLanguage
import `in`.kisancoldlink.app.domain.model.LotSession
import `in`.kisancoldlink.app.domain.repository.AdvisoryRepository
import `in`.kisancoldlink.app.domain.repository.LotRepository
import `in`.kisancoldlink.app.domain.repository.SessionRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class CallUiState(
    val phase: CallPhase = CallPhase.IDLE,
    val language: AppLanguage = AppLanguage.TELUGU,
    val crop: String = "",
    /** Text of whatever Raithanna is saying (or would say when audio is unavailable). */
    val script: String = "",
    val aiNarrated: Boolean = false,
    /** Why audio is missing for the current stage; the text is shown instead. */
    val audioProblem: String? = null,
    val error: AppError? = null,
    val positionMs: Long = 0,
    val durationMs: Long = 0,
    val paused: Boolean = false,
    val reportHasAudio: Boolean = false,
    val savedReportAvailable: Boolean = false,
) {
    val speaking: Boolean get() = phase in CallStateMachine.PLAYING && !paused && durationMs > 0
    val optionsEnabled: Boolean get() = phase == CallPhase.WAITING_FOR_SELECTION
}

@HiltViewModel
class CallViewModel @Inject constructor(
    private val sessions: SessionRepository,
    private val lots: LotRepository,
    private val advisories: AdvisoryRepository,
    private val player: AudioPlayer,
) : ViewModel() {
    private val _state = MutableStateFlow(CallUiState())
    val state: StateFlow<CallUiState> = _state.asStateFlow()

    private var session: LotSession? = null
    private var report: Advisory? = null
    private var retryFrom: CallPhase? = null
    private var work: Job? = null
    private var lastCompletion: Int = -1

    init {
        viewModelScope.launch { player.state.collect(::onPlayback) }
    }

    private fun fire(event: CallEvent): Boolean {
        val next = CallStateMachine.next(_state.value.phase, event, retryFrom) ?: return false
        if (next == CallPhase.ERROR) retryFrom = _state.value.phase
        _state.update { it.copy(phase = next) }
        return true
    }

    /** Idempotent: recomposition or activity recreation calls this again without restarting audio. */
    fun start() {
        if (!fire(CallEvent.Start)) return
        loadLot()
    }

    private fun loadLot() {
        work = viewModelScope.launch {
            val language = sessions.language.first()
            val s = sessions.session.first()
            _state.update { it.copy(language = language, crop = s?.crop(language).orEmpty()) }
            if (s == null) return@launch fail(AppError.Unauthorized("no lot selected"))
            session = s
            _state.update { it.copy(savedReportAvailable = advisories.lastReport(s, language) != null) }
            lots.lotDetail(s).fold(
                onSuccess = { fire(CallEvent.LotLoaded); generate(AdvisoryStage.GREETING) },
                onFailure = { fail(it) },
            )
        }
    }

    private fun fail(error: Throwable) {
        _state.update { it.copy(error = error as? AppError ?: AppError.Server("client_error", error.message ?: "")) }
        fire(CallEvent.Failed)
    }

    private fun generate(stage: AdvisoryStage) {
        val s = session ?: return fail(AppError.Unauthorized("no lot selected"))
        work = viewModelScope.launch {
            advisories.prepare(s, stage, _state.value.language).fold(
                onSuccess = { present(it) },
                onFailure = {
                    // Saying goodbye must never strand the farmer on an error screen.
                    if (stage == AdvisoryStage.GOODBYE) fire(CallEvent.EndCall) else fail(it)
                },
            )
        }
    }

    private fun present(a: Advisory) {
        val hasAudio = a.audioFile != null
        if (a.stage == AdvisoryStage.REPORT) report = a
        _state.update {
            it.copy(script = a.script, aiNarrated = a.aiNarrated, audioProblem = a.audioProblem, error = null,
                positionMs = 0, durationMs = 0, paused = false,
                reportHasAudio = if (a.stage == AdvisoryStage.REPORT) hasAudio else it.reportHasAudio)
        }
        val event = when (a.stage) {
            AdvisoryStage.GREETING -> CallEvent.GreetingReady(hasAudio)
            AdvisoryStage.REPORT -> CallEvent.ReportReady(hasAudio)
            AdvisoryStage.GOODBYE -> CallEvent.GoodbyeReady(hasAudio)
        }
        if (fire(event) && hasAudio) player.play(a.audioFile!!)
    }

    private fun onPlayback(p: PlaybackState) {
        val phase = _state.value.phase
        when (p) {
            is PlaybackState.Playing -> _state.update { it.copy(positionMs = p.positionMs, durationMs = p.durationMs, paused = false) }
            is PlaybackState.Paused -> _state.update { it.copy(positionMs = p.positionMs, durationMs = p.durationMs, paused = true) }
            is PlaybackState.Completed -> if (p.id != lastCompletion) {
                lastCompletion = p.id
                finishPlayback(phase)
            }
            is PlaybackState.Error -> if (phase in CallStateMachine.PLAYING) {
                _state.update { it.copy(audioProblem = "playback error: ${p.message}") }
                finishPlayback(phase)
            }
            else -> Unit
        }
    }

    private fun finishPlayback(phase: CallPhase) {
        when (phase) {
            CallPhase.PLAYING_GREETING -> fire(CallEvent.GreetingFinished)
            CallPhase.PLAYING_REPORT -> fire(CallEvent.ReportFinished)
            CallPhase.PLAYING_GOODBYE -> fire(CallEvent.GoodbyeFinished)
            else -> Unit
        }
    }

    /** Option 1: hear the full report. Ignored unless Raithanna is waiting for a choice. */
    fun pressOne() {
        if (!fire(CallEvent.Press1)) return
        fire(CallEvent.Generate)
        generate(AdvisoryStage.REPORT)
    }

    /** Option 2: polite goodbye, then the call ends. */
    fun pressTwo() {
        if (!fire(CallEvent.Press2)) return
        player.stop()
        fire(CallEvent.Generate)
        generate(AdvisoryStage.GOODBYE)
    }

    fun replay() {
        val file = report?.audioFile ?: return
        _state.update { it.copy(script = report!!.script, positionMs = 0, paused = false) }
        if (fire(CallEvent.Replay)) player.play(file)
    }

    /** Re-request the report when its audio failed (TTS timeout or not configured): text and figures are cached. */
    fun retryAudio() {
        val s = session ?: return
        if (_state.value.phase != CallPhase.REPORT_COMPLETED) return
        work = viewModelScope.launch {
            advisories.prepare(s, AdvisoryStage.REPORT, _state.value.language).onSuccess { a ->
                report = a
                _state.update { it.copy(audioProblem = a.audioProblem, reportHasAudio = a.audioFile != null) }
                if (a.audioFile != null) replay()
            }
        }
    }

    fun retry() {
        if (_state.value.phase != CallPhase.ERROR) return
        val from = retryFrom ?: return
        if (!fire(CallEvent.Retry)) return
        _state.update { it.copy(error = null) }
        when (from) {
            CallPhase.LOADING_LOT -> loadLot()
            CallPhase.GENERATING_GREETING -> generate(AdvisoryStage.GREETING)
            CallPhase.GENERATING_REPORT -> generate(AdvisoryStage.REPORT)
            CallPhase.GENERATING_GOODBYE -> generate(AdvisoryStage.GOODBYE)
            else -> Unit
        }
    }

    /** Offline fallback after a failed report: the last saved report, which the screen labels as saved. */
    fun playSavedReport() {
        val s = session ?: return
        if (_state.value.phase != CallPhase.ERROR || retryFrom != CallPhase.GENERATING_REPORT) return
        viewModelScope.launch {
            val saved = advisories.lastReport(s, _state.value.language) ?: return@launch
            if (fire(CallEvent.Retry)) present(saved)
        }
    }

    fun togglePause() {
        val st = _state.value
        if (st.phase !in CallStateMachine.PLAYING) return
        if (st.paused) player.resume() else player.pause()
    }

    /** App went to the background: pause instead of talking into an empty room. */
    fun onBackground() {
        if (_state.value.phase in CallStateMachine.PLAYING && !_state.value.paused) player.pause()
    }

    fun endCall() {
        work?.cancel()
        player.stop()
        fire(CallEvent.EndCall)
    }

    override fun onCleared() {
        player.stop()
        super.onCleared()
    }
}
