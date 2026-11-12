package `in`.kisancoldlink.app.features.authentication

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import `in`.kisancoldlink.app.R
import `in`.kisancoldlink.app.core.design.BigButton
import `in`.kisancoldlink.app.core.design.KclCard
import `in`.kisancoldlink.app.core.design.KclColors
import `in`.kisancoldlink.app.core.design.LoadingBox
import `in`.kisancoldlink.app.core.design.MessageBox
import `in`.kisancoldlink.app.core.design.RaithannaAvatar
import `in`.kisancoldlink.app.core.design.SecondaryButton
import `in`.kisancoldlink.app.core.networking.AppError
import `in`.kisancoldlink.app.core.utils.Numbers
import `in`.kisancoldlink.app.domain.model.AppLanguage
import `in`.kisancoldlink.app.domain.model.FarmerLot
import `in`.kisancoldlink.app.domain.repository.SessionRepository
import `in`.kisancoldlink.app.domain.usecase.IdentifyFarmerUseCase
import `in`.kisancoldlink.app.domain.usecase.IdentifyInputError
import `in`.kisancoldlink.app.features.call.errorText
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed interface AuthStep {
    data object Form : AuthStep
    data class ChooseLot(val lots: List<FarmerLot>) : AuthStep
    data class Confirm(val lot: FarmerLot, val multiple: List<FarmerLot>?) : AuthStep
    data object Done : AuthStep
}

data class AuthUiState(
    val name: String = "",
    val phone: String = "",
    val inputError: IdentifyInputError? = null,
    val error: AppError? = null,
    val loading: Boolean = false,
    val step: AuthStep = AuthStep.Form,
)

@HiltViewModel
class AuthViewModel @Inject constructor(
    private val identify: IdentifyFarmerUseCase,
    private val sessions: SessionRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(AuthUiState())
    val state: StateFlow<AuthUiState> = _state.asStateFlow()
    val language: StateFlow<AppLanguage> = sessions.language.stateIn(viewModelScope, SharingStarted.Eagerly, AppLanguage.TELUGU)

    fun onName(v: String) = _state.update { it.copy(name = v, inputError = null, error = null) }
    fun onPhone(v: String) = _state.update { it.copy(phone = v.filter { c -> c.isDigit() || c == '+' || c == ' ' }.take(16), inputError = null, error = null) }

    fun submit() {
        if (_state.value.loading) return // ignore double taps
        _state.update { it.copy(loading = true, error = null, inputError = null) }
        viewModelScope.launch {
            when (val r = identify(_state.value.name, _state.value.phone)) {
                is IdentifyFarmerUseCase.Outcome.Invalid -> _state.update { it.copy(loading = false, inputError = r.error) }
                is IdentifyFarmerUseCase.Outcome.Failed -> _state.update { it.copy(loading = false, error = r.error as? AppError) }
                is IdentifyFarmerUseCase.Outcome.Found -> _state.update {
                    it.copy(loading = false, step = if (r.lots.size == 1) AuthStep.Confirm(r.lots[0], null) else AuthStep.ChooseLot(r.lots))
                }
            }
        }
    }

    fun choose(lot: FarmerLot) = _state.update {
        it.copy(step = AuthStep.Confirm(lot, (it.step as? AuthStep.ChooseLot)?.lots))
    }

    fun back() = _state.update {
        val step = it.step
        it.copy(step = if (step is AuthStep.Confirm && step.multiple != null) AuthStep.ChooseLot(step.multiple) else AuthStep.Form)
    }

    fun confirm() {
        val lot = (_state.value.step as? AuthStep.Confirm)?.lot ?: return
        viewModelScope.launch {
            sessions.saveSession(lot.toSession())
            _state.update { it.copy(step = AuthStep.Done) }
        }
    }
}

@Composable
fun AuthScreen(onDone: () -> Unit, viewModel: AuthViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val language by viewModel.language.collectAsStateWithLifecycle()
    if (state.step is AuthStep.Done) {
        androidx.compose.runtime.LaunchedEffect(Unit) { onDone() }
        return
    }
    AuthContent(state, language, viewModel::onName, viewModel::onPhone, viewModel::submit, viewModel::choose, viewModel::confirm, viewModel::back)
}

@Composable
fun AuthContent(
    state: AuthUiState,
    language: AppLanguage,
    onName: (String) -> Unit,
    onPhone: (String) -> Unit,
    onSubmit: () -> Unit,
    onChoose: (FarmerLot) -> Unit,
    onConfirm: () -> Unit,
    onBack: () -> Unit,
) {
    Column(
        Modifier.fillMaxSize().safeDrawingPadding().verticalScroll(rememberScrollState()).padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        RaithannaAvatar(112.dp, description = stringResource(R.string.assistant_name))
        when (val step = state.step) {
            AuthStep.Form, AuthStep.Done -> {
                Text(stringResource(R.string.identify_title), style = MaterialTheme.typography.headlineMedium, color = KclColors.ForestDeep)
                Text(stringResource(R.string.identify_body), style = MaterialTheme.typography.bodyLarge, color = KclColors.Muted)
                OutlinedTextField(
                    state.name, onName, label = { Text(stringResource(R.string.field_name)) }, singleLine = true,
                    textStyle = MaterialTheme.typography.bodyLarge, modifier = Modifier.fillMaxWidth().testTag("name"),
                    isError = state.inputError == IdentifyInputError.NAME_REQUIRED,
                    supportingText = { if (state.inputError == IdentifyInputError.NAME_REQUIRED) Text(stringResource(R.string.error_name_required)) },
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Next),
                )
                OutlinedTextField(
                    state.phone, onPhone, label = { Text(stringResource(R.string.field_phone)) }, singleLine = true,
                    textStyle = MaterialTheme.typography.bodyLarge, modifier = Modifier.fillMaxWidth().testTag("phone"),
                    isError = state.inputError == IdentifyInputError.PHONE_INVALID,
                    supportingText = { if (state.inputError == IdentifyInputError.PHONE_INVALID) Text(stringResource(R.string.error_phone_invalid)) },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone, imeAction = ImeAction.Done),
                )
                if (state.loading) LoadingBox(stringResource(R.string.loading))
                else BigButton(stringResource(R.string.identify_submit), onSubmit, modifier = Modifier.testTag("submit"))
                state.error?.let {
                    // Not registered: the exact Telugu/English sentence from the brief; nothing is created.
                    MessageBox(errorText(it), modifier = Modifier.testTag("auth_error"))
                }
                Text(stringResource(R.string.identify_demo_note), style = MaterialTheme.typography.bodySmall, color = KclColors.Muted)
            }
            is AuthStep.ChooseLot -> {
                Text(stringResource(R.string.choose_lot_title), style = MaterialTheme.typography.headlineMedium, color = KclColors.ForestDeep)
                Text(stringResource(R.string.choose_lot_body), style = MaterialTheme.typography.bodyLarge, color = KclColors.Muted)
                step.lots.forEach { lot -> LotSummaryCard(lot, language, Modifier.clickable { onChoose(lot) }.testTag("lot_${lot.lotId}")) }
                SecondaryButton(stringResource(R.string.confirm_no), onBack)
            }
            is AuthStep.Confirm -> {
                Text(stringResource(R.string.confirm_title), style = MaterialTheme.typography.headlineMedium, color = KclColors.ForestDeep)
                LotSummaryCard(step.lot, language, Modifier, showName = true)
                BigButton(stringResource(R.string.confirm_yes), onConfirm, modifier = Modifier.testTag("confirm"))
                SecondaryButton(stringResource(R.string.confirm_no), onBack)
            }
        }
    }
}

@Composable
fun LotSummaryCard(lot: FarmerLot, language: AppLanguage, modifier: Modifier, showName: Boolean = false) {
    KclCard(modifier) {
        if (showName) Text(lot.farmerName, style = MaterialTheme.typography.titleLarge, color = KclColors.Ink)
        Text(stringResource(R.string.lot_line, lot.crop(language), Numbers.plain(lot.quantityQuintals)),
            style = MaterialTheme.typography.titleMedium, color = KclColors.ForestDeep)
        lot.village?.let { Text(stringResource(R.string.lot_village, it), style = MaterialTheme.typography.bodyMedium) }
        Text(stringResource(R.string.lot_mandis, lot.mandiCount), style = MaterialTheme.typography.bodyMedium, color = KclColors.Muted)
    }
}
