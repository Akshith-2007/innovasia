package `in`.kisancoldlink.app.ui

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.test.ext.junit.runners.AndroidJUnit4
import `in`.kisancoldlink.app.Fixtures
import `in`.kisancoldlink.app.core.design.KisanTheme
import `in`.kisancoldlink.app.core.networking.AppError
import `in`.kisancoldlink.app.core.utils.ProvideLanguage
import `in`.kisancoldlink.app.domain.model.AppLanguage
import `in`.kisancoldlink.app.domain.model.LotDetailResult
import `in`.kisancoldlink.app.domain.usecase.IdentifyInputError
import `in`.kisancoldlink.app.features.authentication.AuthContent
import `in`.kisancoldlink.app.features.authentication.AuthUiState
import `in`.kisancoldlink.app.features.call.CallContent
import `in`.kisancoldlink.app.features.call.CallPhase
import `in`.kisancoldlink.app.features.call.CallUiState
import `in`.kisancoldlink.app.features.home.HomeContent
import `in`.kisancoldlink.app.features.lot.LotUiState
import `in`.kisancoldlink.app.features.onboarding.WelcomeContent
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.annotation.Config

/** Compose UI tests on the JVM (Robolectric): real resources, real Telugu and English strings. */
@RunWith(AndroidJUnit4::class)
@Config(sdk = [34])
class ScreensTest {
    @get:Rule val compose = createComposeRule()

    private fun show(language: AppLanguage = AppLanguage.TELUGU, content: @androidx.compose.runtime.Composable () -> Unit) =
        compose.setContent { ProvideLanguage(language) { KisanTheme { content() } } }

    @Test fun onboardingTeluguByDefaultAndEnglish() {
        var chosen: AppLanguage? = null
        show { WelcomeContent(AppLanguage.TELUGU, { chosen = it }, {}) }
        compose.onNodeWithText("మీ పంటకు మంచి ధర. మీ కష్టానికి మంచి ఫలితం.").assertIsDisplayed()
        compose.onNodeWithTag("lang_en").performClick()
        assertEquals(AppLanguage.ENGLISH, chosen)
    }

    @Test fun onboardingInEnglish() {
        show(AppLanguage.ENGLISH) { WelcomeContent(AppLanguage.ENGLISH, {}, {}) }
        compose.onNodeWithText("A good price for your crop. A good return for your hard work.").assertIsDisplayed()
    }

    @Test fun identificationShowsValidationAndNotRegistered() {
        show { AuthContent(AuthUiState(inputError = IdentifyInputError.PHONE_INVALID), AppLanguage.TELUGU, {}, {}, {}, {}, {}, {}) }
        compose.onNodeWithText("దయచేసి 10 అంకెల మొబైల్ నంబర్ ఇవ్వండి.").assertIsDisplayed()
    }

    @Test fun identificationNotRegisteredMessage() {
        show { AuthContent(AuthUiState(error = AppError.NotRegistered("")), AppLanguage.TELUGU, {}, {}, {}, {}, {}, {}) }
        compose.onNodeWithText("బాబాయ్, మీ వివరాలు ఇంకా నమోదు కాలేదు. దయచేసి మా నిర్వాహకులను సంప్రదించండి.").performScrollTo().assertIsDisplayed()
    }

    @Test fun lotSelectionAndConfirm() {
        val lot = Fixtures.lotView().summary.toDomain()
        var chose = false
        show {
            AuthContent(AuthUiState(step = `in`.kisancoldlink.app.features.authentication.AuthStep.ChooseLot(listOf(lot, lot.copy(lotId = "b")))),
                AppLanguage.TELUGU, {}, {}, {}, { chose = true }, {}, {})
        }
        compose.onNodeWithTag("lot_b").performClick()
        assertEquals(true, chose)
    }

    @Test fun dashboardGreetsBabaiWithCropFromLot() {
        val detail = Fixtures.lotView().toDomain()
        show { HomeContent(LotUiState(loading = false, result = LotDetailResult(detail, false, 0)), {}, {}) }
        compose.onNodeWithTag("greeting").assertIsDisplayed()
        compose.onNodeWithText("నమస్కారం బాబాయ్!").assertIsDisplayed()
        compose.onNodeWithTag("crop_name").assertIsDisplayed()
        compose.onNodeWithText("వరి").assertIsDisplayed()
        compose.onNodeWithText("E2E Test (sample inputs)", substring = true).assertDoesNotExist() // never the farmer's name
        compose.onNodeWithText("నిల్వ ఉన్న అధికారిక సమాచారం, ఈరోజు ప్రత్యక్ష ధర కాదు").performScrollTo().assertIsDisplayed()
        compose.onNodeWithTag("talk").performScrollTo().assertIsDisplayed()
    }

    @Test fun dashboardLabelsCachedData() {
        val detail = Fixtures.lotView().toDomain()
        show { HomeContent(LotUiState(loading = false, result = LotDetailResult(detail, true, 0)), {}, {}) }
        compose.onNodeWithTag("cached_notice").assertIsDisplayed()
    }

    @Test fun dashboardNetworkError() {
        show { HomeContent(LotUiState(loading = false, error = AppError.Network("x")), {}, {}) }
        compose.onNodeWithText("కిసాన్ కోల్డ్ లింక్ సర్వర్ అందుబాటులో లేదు. ఇంటర్నెట్ చూసి మళ్లీ ప్రయత్నించండి.").assertIsDisplayed()
    }

    private fun call(state: CallUiState, onOne: () -> Unit = {}, onTwo: () -> Unit = {}, onReplay: () -> Unit = {}, lang: AppLanguage = AppLanguage.TELUGU) =
        show(lang) { CallContent(state, onOne, onTwo, {}, {}, onReplay, {}, {}, {}, {}, {}) }

    @Test fun callOptionsDisabledWhileGreetingPlays() {
        call(CallUiState(phase = CallPhase.PLAYING_GREETING, script = "బాబాయ్... శుభోదయం!", durationMs = 9000, positionMs = 1000))
        compose.onNodeWithTag("option1").assertIsNotEnabled()
        compose.onNodeWithTag("option2").assertIsNotEnabled()
        compose.onNodeWithTag("wave_active").assertExists()
        compose.onNodeWithText("రైతన్న మాట్లాడుతున్నాడు").assertIsDisplayed()
    }

    @Test fun callOption1AndOption2() {
        var one = 0; var two = 0
        call(CallUiState(phase = CallPhase.WAITING_FOR_SELECTION), { one++ }, { two++ })
        compose.onNodeWithText("అవును, ధరలు చెప్పు").assertIsDisplayed()
        compose.onNodeWithText("వద్దు, తర్వాత చూద్దాం").assertIsDisplayed()
        compose.onNodeWithTag("option1").assertIsEnabled().performClick()
        compose.onNodeWithTag("option2").performClick()
        assertEquals(1, one); assertEquals(1, two)
        compose.onNodeWithTag("wave_idle").assertExists() // no fake speaking/listening animation
    }

    @Test fun callEnglishLabels() {
        call(CallUiState(phase = CallPhase.WAITING_FOR_SELECTION), lang = AppLanguage.ENGLISH)
        compose.onNodeWithText("Yes, tell me the prices").assertIsDisplayed()
        compose.onNodeWithText("No, later").assertIsDisplayed()
    }

    @Test fun callReportCompletedOffersReplay() {
        var replays = 0
        call(CallUiState(phase = CallPhase.REPORT_COMPLETED, script = "report", reportHasAudio = true), onReplay = { replays++ })
        compose.onNodeWithTag("replay").performScrollTo().performClick()
        assertEquals(1, replays)
        compose.onNodeWithText("పూర్తి వివరాలు చూడండి").performScrollTo().assertIsDisplayed()
        compose.onNodeWithTag("home").performScrollTo().assertIsDisplayed()
    }

    @Test fun callAudioUnavailableShowsText() {
        call(CallUiState(phase = CallPhase.WAITING_FOR_SELECTION, script = "బాబాయ్... శుభోదయం!", audioProblem = "not configured"))
        compose.onNodeWithText("ప్రస్తుతం ఆడియో అందుబాటులో లేదు", substring = true).assertIsDisplayed()
        compose.onNodeWithTag("script").performScrollTo().assertIsDisplayed()
    }

    @Test fun callNetworkErrorShowsRetry() {
        call(CallUiState(phase = CallPhase.ERROR, error = AppError.Network("x")))
        compose.onNodeWithText("మళ్లీ ప్రయత్నించండి").performScrollTo().assertIsDisplayed()
    }
}
