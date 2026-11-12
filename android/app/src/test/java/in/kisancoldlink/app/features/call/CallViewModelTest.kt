package `in`.kisancoldlink.app.features.call

import `in`.kisancoldlink.app.FakeAdvisories
import `in`.kisancoldlink.app.FakeLots
import `in`.kisancoldlink.app.FakePlayer
import `in`.kisancoldlink.app.FakeSessions
import `in`.kisancoldlink.app.core.networking.AppError
import `in`.kisancoldlink.app.domain.model.AdvisoryStage
import `in`.kisancoldlink.app.domain.model.AppLanguage
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class CallViewModelTest {
    private val player = FakePlayer()
    private lateinit var advisories: FakeAdvisories
    private lateinit var lots: FakeLots

    @Before fun setUp() = Dispatchers.setMain(UnconfinedTestDispatcher())
    @After fun tearDown() = Dispatchers.resetMain()

    private fun vm(language: AppLanguage = AppLanguage.TELUGU, withAudio: Boolean = true): CallViewModel {
        advisories = FakeAdvisories(withAudio)
        lots = FakeLots()
        return CallViewModel(FakeSessions(language), lots, advisories, player)
    }

    @Test fun greetingPlaysFullyBeforeOptionsActivate() {
        val vm = vm()
        vm.start()
        assertEquals(CallPhase.PLAYING_GREETING, vm.state.value.phase)
        assertFalse(vm.state.value.optionsEnabled)
        assertTrue(vm.state.value.speaking)
        vm.pressOne() // ignored: farmer must hear the opening first
        assertEquals(listOf(AdvisoryStage.GREETING), advisories.requested.map { it.first })
        player.finish()
        assertEquals(CallPhase.WAITING_FOR_SELECTION, vm.state.value.phase)
        assertTrue(vm.state.value.optionsEnabled)
        assertFalse(vm.state.value.speaking)
    }

    @Test fun greetingUsesTheLotCropNotTomato() {
        val vm = vm()
        vm.start()
        assertTrue(vm.state.value.script.contains("వరి"))
        assertFalse(vm.state.value.script.contains("టమాటా"))
        assertEquals("వరి", vm.state.value.crop)
    }

    @Test fun option1PlaysReportThenAllowsReplay() {
        val vm = vm()
        vm.start(); player.finish()
        vm.pressOne()
        vm.pressOne() // duplicate tap
        assertEquals(listOf(AdvisoryStage.GREETING, AdvisoryStage.REPORT), advisories.requested.map { it.first })
        assertEquals(CallPhase.PLAYING_REPORT, vm.state.value.phase)
        player.finish()
        assertEquals(CallPhase.REPORT_COMPLETED, vm.state.value.phase)
        vm.replay()
        assertEquals(CallPhase.PLAYING_REPORT, vm.state.value.phase)
        assertEquals(listOf("GREETING.mp3", "REPORT.mp3", "REPORT.mp3"), player.played)
        player.finish()
        assertEquals(CallPhase.REPORT_COMPLETED, vm.state.value.phase) // does not restart the call
    }

    @Test fun option2SaysGoodbyeAndEnds() {
        val vm = vm()
        vm.start(); player.finish()
        vm.pressTwo()
        assertEquals(CallPhase.PLAYING_GOODBYE, vm.state.value.phase)
        assertTrue(vm.state.value.script.startsWith("సరే బాబాయ్!"))
        player.finish()
        assertEquals(CallPhase.CALL_COMPLETED, vm.state.value.phase)
    }

    @Test fun englishLanguageRequestsEnglish() {
        val vm = vm(AppLanguage.ENGLISH)
        vm.start()
        assertEquals(AppLanguage.ENGLISH, advisories.requested.single().second)
        assertTrue(vm.state.value.script.contains("Paddy"))
    }

    @Test fun ttsUnavailableShowsTextAndContinues() {
        val vm = vm(withAudio = false)
        vm.start()
        assertEquals(CallPhase.WAITING_FOR_SELECTION, vm.state.value.phase)
        assertNotNull(vm.state.value.audioProblem)
        assertTrue(vm.state.value.script.isNotBlank())
        assertTrue(player.played.isEmpty())
        vm.pressOne()
        assertEquals(CallPhase.REPORT_COMPLETED, vm.state.value.phase)
        assertFalse(vm.state.value.reportHasAudio)
    }

    @Test fun playbackErrorDoesNotStrandTheFarmer() {
        val vm = vm()
        vm.start()
        player.fail()
        assertEquals(CallPhase.WAITING_FOR_SELECTION, vm.state.value.phase)
        assertNotNull(vm.state.value.audioProblem)
    }

    @Test fun backendDownThenRetry() {
        advisories = FakeAdvisories(); lots = FakeLots(fail = AppError.Network("offline"))
        val vm = CallViewModel(FakeSessions(), lots, advisories, player)
        vm.start()
        assertEquals(CallPhase.ERROR, vm.state.value.phase)
        assertTrue(vm.state.value.error is AppError.Network)
        assertTrue(advisories.requested.isEmpty()) // no recommendation without backend data
        lots.fail = null
        vm.retry()
        assertEquals(CallPhase.PLAYING_GREETING, vm.state.value.phase)
    }

    @Test fun reportFailureOffersRetry() {
        val vm = vm()
        advisories.failStage = AdvisoryStage.REPORT
        vm.start(); player.finish(); vm.pressOne()
        assertEquals(CallPhase.ERROR, vm.state.value.phase)
        advisories.failStage = null
        vm.retry()
        assertEquals(CallPhase.PLAYING_REPORT, vm.state.value.phase)
    }

    @Test fun goodbyeFailureStillEndsPolitely() {
        val vm = vm()
        advisories.failStage = AdvisoryStage.GOODBYE
        vm.start(); player.finish(); vm.pressTwo()
        assertEquals(CallPhase.CALL_COMPLETED, vm.state.value.phase)
    }

    @Test fun startIsIdempotentAndBackgroundPauses() {
        val vm = vm()
        vm.start(); vm.start(); vm.start()
        assertEquals(1, lots.calls)
        assertEquals(1, player.played.size)
        vm.onBackground()
        assertTrue(vm.state.value.paused)
        assertFalse(vm.state.value.speaking)
        vm.togglePause()
        assertFalse(vm.state.value.paused)
    }

    @Test fun endCallStopsAudio() {
        val vm = vm()
        vm.start()
        vm.endCall()
        assertEquals(CallPhase.CALL_COMPLETED, vm.state.value.phase)
        player.finish() // late completion is ignored
        assertEquals(CallPhase.CALL_COMPLETED, vm.state.value.phase)
    }
}
