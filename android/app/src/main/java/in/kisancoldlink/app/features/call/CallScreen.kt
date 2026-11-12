package `in`.kisancoldlink.app.features.call

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CallEnd
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Replay
import androidx.compose.material.icons.filled.Analytics
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import `in`.kisancoldlink.app.R
import `in`.kisancoldlink.app.core.design.BigButton
import `in`.kisancoldlink.app.core.design.KclCard
import `in`.kisancoldlink.app.core.design.KclColors
import `in`.kisancoldlink.app.core.design.MessageBox
import `in`.kisancoldlink.app.core.design.NumberOptionButton
import `in`.kisancoldlink.app.core.design.RaithannaAvatar
import `in`.kisancoldlink.app.core.design.SecondaryButton
import `in`.kisancoldlink.app.core.design.Waveform
import `in`.kisancoldlink.app.core.networking.AppError

@Composable
fun CallScreen(onFinished: () -> Unit, onOpenAnalysis: () -> Unit, viewModel: CallViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { viewModel.start() } // start() is idempotent: recomposition never restarts audio
    LifecycleEventEffect(Lifecycle.Event.ON_STOP) { viewModel.onBackground() }
    LaunchedEffect(state.phase) { if (state.phase == CallPhase.CALL_COMPLETED) onFinished() }
    CallContent(
        state = state,
        onPressOne = viewModel::pressOne,
        onPressTwo = viewModel::pressTwo,
        onEnd = viewModel::endCall,
        onTogglePause = viewModel::togglePause,
        onReplay = viewModel::replay,
        onRetry = viewModel::retry,
        onRetryAudio = viewModel::retryAudio,
        onPlaySaved = viewModel::playSavedReport,
        onAnalysis = onOpenAnalysis,
        onHome = viewModel::endCall,
    )
}

@Composable
fun CallContent(
    state: CallUiState,
    onPressOne: () -> Unit,
    onPressTwo: () -> Unit,
    onEnd: () -> Unit,
    onTogglePause: () -> Unit,
    onReplay: () -> Unit,
    onRetry: () -> Unit,
    onRetryAudio: () -> Unit,
    onPlaySaved: () -> Unit,
    onAnalysis: () -> Unit,
    onHome: () -> Unit,
) {
    Column(
        Modifier.fillMaxSize().background(KclColors.ForestDeep).safeDrawingPadding().verticalScroll(rememberScrollState())
            .padding(20.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Text(stringResource(R.string.call_kisan), style = MaterialTheme.typography.labelMedium, color = KclColors.Sage)
        RaithannaAvatar(176.dp, speaking = state.speaking, description = stringResource(R.string.assistant_name))
        Text(stringResource(R.string.assistant_name), style = MaterialTheme.typography.displaySmall, color = KclColors.White)
        Text(statusText(state), style = MaterialTheme.typography.titleMedium, color = KclColors.Amber,
            modifier = Modifier.testTag("call_status"), textAlign = TextAlign.Center)
        Waveform(active = state.speaking, modifier = Modifier.testTag(if (state.speaking) "wave_active" else "wave_idle"))
        if (state.phase in CallStateMachine.PLAYING && state.durationMs > 0) {
            LinearProgressIndicator(
                progress = { (state.positionMs.toFloat() / state.durationMs).coerceIn(0f, 1f) },
                modifier = Modifier.fillMaxWidth(), color = KclColors.Amber, trackColor = KclColors.Forest,
            )
        }

        state.audioProblem?.let {
            MessageBox(stringResource(R.string.audio_unavailable, it), isError = false)
        }

        when (state.phase) {
            CallPhase.PLAYING_GREETING, CallPhase.WAITING_FOR_SELECTION -> Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                NumberOptionButton(stringResource(R.string.option1_number), stringResource(R.string.option1_label), onPressOne,
                    enabled = state.optionsEnabled, primary = true, modifier = Modifier.weight(1f).testTag("option1"))
                NumberOptionButton(stringResource(R.string.option2_number), stringResource(R.string.option2_label), onPressTwo,
                    enabled = state.optionsEnabled, primary = false, modifier = Modifier.weight(1f).testTag("option2"))
            }
            CallPhase.REPORT_COMPLETED -> Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                if (state.reportHasAudio) BigButton(stringResource(R.string.replay_report), onReplay, icon = Icons.Filled.Replay,
                    container = KclColors.Amber, content = KclColors.Ink, modifier = Modifier.testTag("replay"))
                if (state.audioProblem != null) SecondaryButton(stringResource(R.string.retry_audio), onRetryAudio, icon = Icons.Filled.Refresh)
                BigButton(stringResource(R.string.view_analysis), onAnalysis, icon = Icons.Filled.Analytics, container = KclColors.White,
                    content = KclColors.Forest)
                BigButton(stringResource(R.string.return_home), onHome, icon = Icons.Filled.Home, container = KclColors.Forest,
                    modifier = Modifier.testTag("home"))
            }
            CallPhase.ERROR -> {
                MessageBox(errorText(state.error), action = stringResource(R.string.retry), onAction = onRetry)
                if (state.savedReportAvailable) SecondaryButton(stringResource(R.string.replay_report), onPlaySaved)
            }
            else -> Unit
        }

        if (state.phase in CallStateMachine.PLAYING) {
            SecondaryButton(
                stringResource(if (state.paused) R.string.resume else R.string.pause), onTogglePause,
                icon = if (state.paused) Icons.Filled.PlayArrow else Icons.Filled.Pause,
            )
        }

        if (state.script.isNotBlank()) {
            KclCard(Modifier.testTag("script")) {
                Text(stringResource(R.string.show_text), style = MaterialTheme.typography.titleMedium, color = KclColors.ForestDeep)
                Text(state.script, style = MaterialTheme.typography.bodyLarge, color = KclColors.Ink)
                if (state.phase in setOf(CallPhase.PLAYING_REPORT, CallPhase.REPORT_COMPLETED)) {
                    Text(stringResource(if (state.aiNarrated) R.string.narration_ai else R.string.narration_template),
                        style = MaterialTheme.typography.bodySmall, color = KclColors.Muted)
                }
            }
        }

        if (state.phase != CallPhase.REPORT_COMPLETED && state.phase != CallPhase.CALL_COMPLETED) {
            Spacer(Modifier.height(4.dp))
            BigButton(stringResource(R.string.end_call), onEnd, icon = Icons.Filled.CallEnd, container = KclColors.Danger,
                modifier = Modifier.testTag("end_call"))
        }
    }
}

@Composable
private fun statusText(state: CallUiState): String = when (state.phase) {
    CallPhase.IDLE, CallPhase.LOADING_LOT -> stringResource(R.string.call_connecting)
    CallPhase.GENERATING_GREETING, CallPhase.PRESSED_1, CallPhase.PRESSED_2,
    CallPhase.GENERATING_REPORT, CallPhase.GENERATING_GOODBYE -> stringResource(R.string.call_preparing)
    CallPhase.PLAYING_GREETING, CallPhase.PLAYING_REPORT, CallPhase.PLAYING_GOODBYE ->
        stringResource(if (state.paused) R.string.call_paused else R.string.call_speaking)
    CallPhase.WAITING_FOR_SELECTION -> stringResource(R.string.call_choose)
    CallPhase.REPORT_COMPLETED -> stringResource(R.string.call_report_done)
    CallPhase.CALL_COMPLETED -> stringResource(R.string.call_ended)
    CallPhase.ERROR -> errorText(state.error)
}

@Composable
fun errorText(error: AppError?): String = when (error) {
    is AppError.Network -> stringResource(R.string.error_network)
    is AppError.Unauthorized -> stringResource(R.string.error_session)
    is AppError.NotRegistered -> stringResource(R.string.not_registered)
    is AppError.Server -> stringResource(R.string.error_generic, error.message ?: error.code)
    null -> stringResource(R.string.error_generic, "")
}
