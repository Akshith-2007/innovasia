package `in`.kisancoldlink.app.features.settings

import android.Manifest
import android.content.Context
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import `in`.kisancoldlink.app.R
import `in`.kisancoldlink.app.core.design.KclCard
import `in`.kisancoldlink.app.core.design.KclColors
import `in`.kisancoldlink.app.core.design.SecondaryButton
import `in`.kisancoldlink.app.core.design.SectionTitle
import `in`.kisancoldlink.app.data.local.LocalFiles
import `in`.kisancoldlink.app.domain.model.AppLanguage
import `in`.kisancoldlink.app.domain.model.LotSession
import `in`.kisancoldlink.app.domain.repository.ReminderSettings
import `in`.kisancoldlink.app.domain.repository.SessionRepository
import `in`.kisancoldlink.app.features.onboarding.LanguageButton
import `in`.kisancoldlink.app.notifications.ReminderScheduler
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import java.util.Locale
import javax.inject.Inject

@HiltViewModel
class ProfileViewModel @Inject constructor(
    private val sessions: SessionRepository,
    private val files: LocalFiles,
    @ApplicationContext private val context: Context,
) : ViewModel() {
    val language: StateFlow<AppLanguage> = sessions.language.stateIn(viewModelScope, SharingStarted.Eagerly, AppLanguage.TELUGU)
    val session: StateFlow<LotSession?> = sessions.session.stateIn(viewModelScope, SharingStarted.Eagerly, null)
    val reminder: StateFlow<ReminderSettings> = sessions.reminder.stateIn(viewModelScope, SharingStarted.Eagerly, ReminderSettings())

    fun setLanguage(l: AppLanguage) = viewModelScope.launch { sessions.setLanguage(l) }

    fun setReminder(s: ReminderSettings) = viewModelScope.launch {
        sessions.setReminder(s)
        ReminderScheduler.apply(context, s)
    }

    fun signOut(then: () -> Unit) = viewModelScope.launch {
        ReminderScheduler.apply(context, ReminderSettings(enabled = false))
        sessions.clearSession()
        files.clearAll()
        then()
    }
}

private val TIMES = listOf(6 to 0, 7 to 0, 8 to 0, 9 to 0, 18 to 0, 19 to 0)

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun ProfileScreen(onSignedOut: () -> Unit, viewModel: ProfileViewModel = hiltViewModel()) {
    val language by viewModel.language.collectAsStateWithLifecycle()
    val session by viewModel.session.collectAsStateWithLifecycle()
    val reminder by viewModel.reminder.collectAsStateWithLifecycle()
    val askPermission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        viewModel.setReminder(reminder.copy(enabled = granted))
    }
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(18.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Text(stringResource(R.string.profile_title), style = MaterialTheme.typography.headlineMedium, color = KclColors.ForestDeep)
        session?.let {
            KclCard {
                SectionTitle(stringResource(R.string.profile_lot))
                Text(it.crop(language), style = MaterialTheme.typography.titleLarge)
            }
        }
        KclCard {
            SectionTitle(stringResource(R.string.language))
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                LanguageButton(stringResource(R.string.language_telugu), language == AppLanguage.TELUGU, Modifier.weight(1f)) { viewModel.setLanguage(AppLanguage.TELUGU) }
                LanguageButton(stringResource(R.string.language_english), language == AppLanguage.ENGLISH, Modifier.weight(1f)) { viewModel.setLanguage(AppLanguage.ENGLISH) }
            }
        }
        KclCard {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Text(stringResource(R.string.reminders), style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
                Switch(checked = reminder.enabled, onCheckedChange = { on ->
                    if (on && Build.VERSION.SDK_INT >= 33) askPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
                    else viewModel.setReminder(reminder.copy(enabled = on))
                })
            }
            Text(stringResource(R.string.reminders_body), style = MaterialTheme.typography.bodyMedium, color = KclColors.Muted)
            if (reminder.enabled) {
                Text(stringResource(R.string.reminder_time, String.format(Locale.US, "%02d:%02d", reminder.hour, reminder.minute)),
                    style = MaterialTheme.typography.bodyLarge)
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    TIMES.forEach { (h, m) ->
                        FilterChip(selected = reminder.hour == h && reminder.minute == m,
                            onClick = { viewModel.setReminder(reminder.copy(hour = h, minute = m)) },
                            label = { Text(String.format(Locale.US, "%02d:%02d", h, m), style = MaterialTheme.typography.labelLarge) })
                    }
                }
            }
        }
        SecondaryButton(stringResource(R.string.sign_out), { viewModel.signOut(onSignedOut) })
    }
}
