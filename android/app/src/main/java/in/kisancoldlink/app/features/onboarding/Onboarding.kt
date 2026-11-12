package `in`.kisancoldlink.app.features.onboarding

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import `in`.kisancoldlink.app.R
import `in`.kisancoldlink.app.core.design.BigButton
import `in`.kisancoldlink.app.core.design.KclColors
import `in`.kisancoldlink.app.core.design.RaithannaAvatar
import `in`.kisancoldlink.app.core.design.SecondaryButton
import `in`.kisancoldlink.app.domain.model.AppLanguage
import `in`.kisancoldlink.app.domain.repository.SessionRepository
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class OnboardingViewModel @Inject constructor(private val sessions: SessionRepository) : ViewModel() {
    val language: StateFlow<AppLanguage> = sessions.language.stateIn(viewModelScope, SharingStarted.Eagerly, AppLanguage.TELUGU)
    fun choose(language: AppLanguage) = viewModelScope.launch { sessions.setLanguage(language) }
    fun finish(then: () -> Unit) = viewModelScope.launch { sessions.setOnboarded(); then() }
}

@Composable
fun WelcomeScreen(onContinue: () -> Unit, viewModel: OnboardingViewModel = hiltViewModel()) {
    val language by viewModel.language.collectAsStateWithLifecycle()
    WelcomeContent(language, viewModel::choose) { viewModel.finish(onContinue) }
}

@Composable
fun WelcomeContent(language: AppLanguage, onChoose: (AppLanguage) -> Unit, onContinue: () -> Unit) {
    Column(
        Modifier.fillMaxSize().safeDrawingPadding().verticalScroll(rememberScrollState()).padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(18.dp),
    ) {
        Text(stringResource(R.string.app_name), style = MaterialTheme.typography.titleLarge, color = KclColors.Forest)
        RaithannaAvatar(168.dp, description = stringResource(R.string.assistant_name))
        Text(stringResource(R.string.welcome_heading), style = MaterialTheme.typography.headlineMedium,
            color = KclColors.ForestDeep, textAlign = TextAlign.Center, modifier = Modifier.testTag("welcome_heading"))
        Text(stringResource(R.string.welcome_body), style = MaterialTheme.typography.bodyLarge, color = KclColors.Muted, textAlign = TextAlign.Center)
        Text(stringResource(R.string.choose_language), style = MaterialTheme.typography.titleMedium)
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            LanguageButton(stringResource(R.string.language_telugu), language == AppLanguage.TELUGU, Modifier.weight(1f).testTag("lang_te")) { onChoose(AppLanguage.TELUGU) }
            LanguageButton(stringResource(R.string.language_english), language == AppLanguage.ENGLISH, Modifier.weight(1f).testTag("lang_en")) { onChoose(AppLanguage.ENGLISH) }
        }
        BigButton(stringResource(R.string.continue_label), onContinue, modifier = Modifier.testTag("continue"))
    }
}

@Composable
fun LanguageButton(label: String, selected: Boolean, modifier: Modifier, onClick: () -> Unit) {
    if (selected) BigButton(label, onClick, modifier) else SecondaryButton(label, onClick, modifier)
}
