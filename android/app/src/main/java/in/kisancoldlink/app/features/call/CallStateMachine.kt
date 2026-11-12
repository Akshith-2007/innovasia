package `in`.kisancoldlink.app.features.call

/** Advisory call phases, exactly as in the product brief (section 10), plus ERROR for failures. */
enum class CallPhase {
    IDLE,
    LOADING_LOT,
    GENERATING_GREETING,
    PLAYING_GREETING,
    WAITING_FOR_SELECTION,
    PRESSED_1,
    PRESSED_2,
    GENERATING_REPORT,
    GENERATING_GOODBYE,
    PLAYING_REPORT,
    PLAYING_GOODBYE,
    REPORT_COMPLETED,
    CALL_COMPLETED,
    ERROR,
}

sealed interface CallEvent {
    data object Start : CallEvent
    data object LotLoaded : CallEvent
    /** [hasAudio] false = TTS unavailable: the text is shown and the call continues without audio. */
    data class GreetingReady(val hasAudio: Boolean) : CallEvent
    data object GreetingFinished : CallEvent
    data object Press1 : CallEvent
    data object Press2 : CallEvent
    data object Generate : CallEvent
    data class ReportReady(val hasAudio: Boolean) : CallEvent
    data object ReportFinished : CallEvent
    data class GoodbyeReady(val hasAudio: Boolean) : CallEvent
    data object GoodbyeFinished : CallEvent
    data object Replay : CallEvent
    data object Failed : CallEvent
    data object Retry : CallEvent
    data object EndCall : CallEvent
}

/**
 * Pure transition function. Returns null when an event does not apply in a phase, which is how duplicate
 * presses, presses during the greeting and late audio callbacks are ignored.
 */
object CallStateMachine {
    fun next(phase: CallPhase, event: CallEvent, retryFrom: CallPhase? = null): CallPhase? = when {
        event is CallEvent.EndCall -> if (phase == CallPhase.CALL_COMPLETED) null else CallPhase.CALL_COMPLETED
        phase == CallPhase.IDLE && event is CallEvent.Start -> CallPhase.LOADING_LOT
        phase == CallPhase.LOADING_LOT && event is CallEvent.LotLoaded -> CallPhase.GENERATING_GREETING
        phase == CallPhase.GENERATING_GREETING && event is CallEvent.GreetingReady ->
            if (event.hasAudio) CallPhase.PLAYING_GREETING else CallPhase.WAITING_FOR_SELECTION
        phase == CallPhase.PLAYING_GREETING && event is CallEvent.GreetingFinished -> CallPhase.WAITING_FOR_SELECTION
        phase == CallPhase.WAITING_FOR_SELECTION && event is CallEvent.Press1 -> CallPhase.PRESSED_1
        phase == CallPhase.WAITING_FOR_SELECTION && event is CallEvent.Press2 -> CallPhase.PRESSED_2
        phase == CallPhase.PRESSED_1 && event is CallEvent.Generate -> CallPhase.GENERATING_REPORT
        phase == CallPhase.PRESSED_2 && event is CallEvent.Generate -> CallPhase.GENERATING_GOODBYE
        phase == CallPhase.GENERATING_REPORT && event is CallEvent.ReportReady ->
            if (event.hasAudio) CallPhase.PLAYING_REPORT else CallPhase.REPORT_COMPLETED
        phase == CallPhase.PLAYING_REPORT && event is CallEvent.ReportFinished -> CallPhase.REPORT_COMPLETED
        phase == CallPhase.REPORT_COMPLETED && event is CallEvent.Replay -> CallPhase.PLAYING_REPORT
        phase == CallPhase.GENERATING_GOODBYE && event is CallEvent.GoodbyeReady ->
            if (event.hasAudio) CallPhase.PLAYING_GOODBYE else CallPhase.CALL_COMPLETED
        phase == CallPhase.PLAYING_GOODBYE && event is CallEvent.GoodbyeFinished -> CallPhase.CALL_COMPLETED
        event is CallEvent.Failed && phase in RETRYABLE -> CallPhase.ERROR
        phase == CallPhase.ERROR && event is CallEvent.Retry -> retryFrom
        else -> null
    }

    /** Phases that wait on the network and can fail into ERROR (and be retried from). */
    val RETRYABLE = setOf(CallPhase.LOADING_LOT, CallPhase.GENERATING_GREETING, CallPhase.GENERATING_REPORT, CallPhase.GENERATING_GOODBYE)

    /** Phases in which Raithanna's audio is (or should be) playing. */
    val PLAYING = setOf(CallPhase.PLAYING_GREETING, CallPhase.PLAYING_REPORT, CallPhase.PLAYING_GOODBYE)
}
