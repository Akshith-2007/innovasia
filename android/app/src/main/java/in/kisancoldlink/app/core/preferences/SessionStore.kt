package `in`.kisancoldlink.app.core.preferences

import android.content.Context
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import `in`.kisancoldlink.app.domain.model.AppLanguage
import `in`.kisancoldlink.app.domain.model.LotSession
import `in`.kisancoldlink.app.domain.repository.ReminderSettings
import `in`.kisancoldlink.app.domain.repository.SessionRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.dataStore by preferencesDataStore(name = "kisan_session")

/** DataStore: language, onboarding, the selected lot reference + token, reminder settings. No phone number. */
@Singleton
class SessionStore @Inject constructor(@ApplicationContext private val context: Context) : SessionRepository {
    private object K {
        val language = stringPreferencesKey("language")
        val onboarded = booleanPreferencesKey("onboarded")
        val lotId = stringPreferencesKey("lot_id")
        val token = stringPreferencesKey("lot_token")
        val commodity = stringPreferencesKey("commodity")
        val cropTe = stringPreferencesKey("crop_te")
        val cropEn = stringPreferencesKey("crop_en")
        val reminderOn = booleanPreferencesKey("reminder_on")
        val reminderHour = intPreferencesKey("reminder_hour")
        val reminderMinute = intPreferencesKey("reminder_minute")
    }

    private val prefs: Flow<Preferences> get() = context.dataStore.data

    override val language: Flow<AppLanguage> = prefs.map { AppLanguage.fromCode(it[K.language]) }
    override val onboarded: Flow<Boolean> = prefs.map { it[K.onboarded] == true }
    override val session: Flow<LotSession?> = prefs.map { p ->
        val id = p[K.lotId]
        val token = p[K.token]
        if (id.isNullOrBlank() || token.isNullOrBlank()) null
        else LotSession(id, token, p[K.commodity].orEmpty(), p[K.cropTe].orEmpty(), p[K.cropEn].orEmpty())
    }
    override val reminder: Flow<ReminderSettings> = prefs.map {
        ReminderSettings(it[K.reminderOn] == true, it[K.reminderHour] ?: 7, it[K.reminderMinute] ?: 0)
    }

    override suspend fun setLanguage(language: AppLanguage) {
        context.dataStore.edit { it[K.language] = language.code }
    }

    override suspend fun setOnboarded() {
        context.dataStore.edit { it[K.onboarded] = true }
    }

    override suspend fun saveSession(session: LotSession) {
        context.dataStore.edit {
            it[K.lotId] = session.lotId
            it[K.token] = session.token
            it[K.commodity] = session.commodity
            it[K.cropTe] = session.cropTe
            it[K.cropEn] = session.cropEn
        }
    }

    override suspend fun clearSession() {
        context.dataStore.edit {
            listOf(K.lotId, K.token, K.commodity, K.cropTe, K.cropEn).forEach { k -> it.remove(k) }
            it[K.reminderOn] = false
        }
    }

    override suspend fun setReminder(settings: ReminderSettings) {
        context.dataStore.edit {
            it[K.reminderOn] = settings.enabled
            it[K.reminderHour] = settings.hour
            it[K.reminderMinute] = settings.minute
        }
    }
}
