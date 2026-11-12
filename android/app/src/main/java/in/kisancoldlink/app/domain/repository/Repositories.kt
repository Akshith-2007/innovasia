package `in`.kisancoldlink.app.domain.repository

import `in`.kisancoldlink.app.domain.model.Advisory
import `in`.kisancoldlink.app.domain.model.AdvisoryStage
import `in`.kisancoldlink.app.domain.model.AppLanguage
import `in`.kisancoldlink.app.domain.model.FarmerLot
import `in`.kisancoldlink.app.domain.model.LivePrice
import `in`.kisancoldlink.app.domain.model.LotDetailResult
import `in`.kisancoldlink.app.domain.model.LotSession
import kotlinx.coroutines.flow.Flow

interface FarmerRepository {
    /** Admin-created lots whose farmer name AND mobile number both match. Never creates a lot. */
    suspend fun identify(name: String, phone: String): Result<List<FarmerLot>>
}

interface SessionRepository {
    val language: Flow<AppLanguage>
    val onboarded: Flow<Boolean>
    val session: Flow<LotSession?>
    val reminder: Flow<ReminderSettings>
    suspend fun setLanguage(language: AppLanguage)
    suspend fun setOnboarded()
    suspend fun saveSession(session: LotSession)
    suspend fun clearSession()
    suspend fun setReminder(settings: ReminderSettings)
}

data class ReminderSettings(val enabled: Boolean = false, val hour: Int = 7, val minute: Int = 0)

interface LotRepository {
    /** Fresh comparison from the backend; on network failure the last saved copy, flagged as cached. */
    suspend fun lotDetail(session: LotSession, forceRefresh: Boolean = false): Result<LotDetailResult>
    suspend fun livePrice(session: LotSession, mandi: String): Result<LivePrice?>
}

interface AdvisoryRepository {
    suspend fun prepare(session: LotSession, stage: AdvisoryStage, language: AppLanguage): Result<Advisory>
    /** The last report that was prepared successfully, for replay without network. */
    suspend fun lastReport(session: LotSession, language: AppLanguage): Advisory?
}
