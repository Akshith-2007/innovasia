package `in`.kisancoldlink.app.features.call

import `in`.kisancoldlink.app.features.call.CallEvent.*
import `in`.kisancoldlink.app.features.call.CallPhase.*
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class CallStateMachineTest {
    private fun run(vararg events: CallEvent): CallPhase =
        events.fold(IDLE) { p, e -> CallStateMachine.next(p, e) ?: error("$e not allowed in $p") }

    @Test fun option1Path() {
        assertEquals(REPORT_COMPLETED, run(Start, LotLoaded, GreetingReady(true), GreetingFinished, Press1, Generate, ReportReady(true), ReportFinished))
    }

    @Test fun option2Path() {
        assertEquals(CALL_COMPLETED, run(Start, LotLoaded, GreetingReady(true), GreetingFinished, Press2, Generate, GoodbyeReady(true), GoodbyeFinished))
    }

    @Test fun optionsIgnoredUntilGreetingFinished() {
        assertNull(CallStateMachine.next(PLAYING_GREETING, Press1))
        assertNull(CallStateMachine.next(PLAYING_GREETING, Press2))
        assertNull(CallStateMachine.next(GENERATING_GREETING, Press1))
    }

    @Test fun duplicatePressesIgnored() {
        assertNull(CallStateMachine.next(PRESSED_1, Press1))
        assertNull(CallStateMachine.next(GENERATING_REPORT, Press1))
        assertNull(CallStateMachine.next(PLAYING_REPORT, Press2))
        assertNull(CallStateMachine.next(PRESSED_2, Press1))
    }

    @Test fun withoutAudioTheTextFlowContinues() {
        assertEquals(WAITING_FOR_SELECTION, run(Start, LotLoaded, GreetingReady(false)))
        assertEquals(REPORT_COMPLETED, run(Start, LotLoaded, GreetingReady(false), Press1, Generate, ReportReady(false)))
        assertEquals(CALL_COMPLETED, run(Start, LotLoaded, GreetingReady(false), Press2, Generate, GoodbyeReady(false)))
    }

    @Test fun replayOnlyAfterReport() {
        assertEquals(PLAYING_REPORT, CallStateMachine.next(REPORT_COMPLETED, Replay))
        assertNull(CallStateMachine.next(WAITING_FOR_SELECTION, Replay))
    }

    @Test fun failureAndRetryReturnToFailedStep() {
        assertEquals(ERROR, CallStateMachine.next(GENERATING_REPORT, Failed))
        assertEquals(GENERATING_REPORT, CallStateMachine.next(ERROR, Retry, retryFrom = GENERATING_REPORT))
        assertNull(CallStateMachine.next(PLAYING_REPORT, Failed)) // playback problems are not network failures
    }

    @Test fun endCallFromAnywhereButOnce() {
        listOf(LOADING_LOT, PLAYING_GREETING, WAITING_FOR_SELECTION, PLAYING_REPORT, REPORT_COMPLETED, ERROR).forEach {
            assertEquals(CALL_COMPLETED, CallStateMachine.next(it, EndCall))
        }
        assertNull(CallStateMachine.next(CALL_COMPLETED, EndCall))
    }
}
