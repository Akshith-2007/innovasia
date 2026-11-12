package `in`.kisancoldlink.app.notifications

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import dagger.hilt.EntryPoint
import dagger.hilt.InstallIn
import dagger.hilt.android.EntryPointAccessors
import dagger.hilt.components.SingletonComponent
import `in`.kisancoldlink.app.MainActivity
import `in`.kisancoldlink.app.R
import `in`.kisancoldlink.app.core.utils.localized
import `in`.kisancoldlink.app.domain.repository.LotRepository
import `in`.kisancoldlink.app.domain.repository.ReminderSettings
import `in`.kisancoldlink.app.domain.repository.SessionRepository
import kotlinx.coroutines.flow.first
import java.time.Duration
import java.time.LocalDateTime
import java.time.LocalTime
import java.util.concurrent.TimeUnit

const val EXTRA_OPEN_CALL = "open_raithanna_call"
private const val CHANNEL_ID = "daily_prices"
private const val WORK_NAME = "raithanna_daily_reminder"

object ReminderScheduler {
    /** Minutes until the next [hour]:[minute] (tomorrow if that time has passed today). */
    fun delayUntil(now: LocalDateTime, hour: Int, minute: Int): Duration {
        var next = now.with(LocalTime.of(hour, minute))
        if (!next.isAfter(now)) next = next.plusDays(1)
        return Duration.between(now, next)
    }

    fun apply(context: Context, settings: ReminderSettings) {
        val wm = WorkManager.getInstance(context)
        if (!settings.enabled) {
            wm.cancelUniqueWork(WORK_NAME)
            return
        }
        val delay = delayUntil(LocalDateTime.now(), settings.hour, settings.minute)
        val request = PeriodicWorkRequestBuilder<ReminderWorker>(24, TimeUnit.HOURS)
            .setInitialDelay(delay.toMinutes(), TimeUnit.MINUTES)
            .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
            .build()
        wm.enqueueUniquePeriodicWork(WORK_NAME, ExistingPeriodicWorkPolicy.UPDATE, request)
    }
}

@EntryPoint
@InstallIn(SingletonComponent::class)
interface ReminderEntryPoint {
    fun sessions(): SessionRepository
    fun lots(): LotRepository
}

/** Once a day. Notifies only if the backend still serves this farmer's lot right now (no "ready" claims otherwise). */
class ReminderWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        val deps = EntryPointAccessors.fromApplication(applicationContext, ReminderEntryPoint::class.java)
        val settings = deps.sessions().reminder.first()
        val session = deps.sessions().session.first() ?: return Result.success()
        if (!settings.enabled) return Result.success()
        val fresh = deps.lots().lotDetail(session, forceRefresh = true).getOrNull()
        if (fresh == null || fresh.fromCache) return Result.success() // backend data unavailable: stay quiet
        Notifications.showDailyReminder(applicationContext.localized(deps.sessions().language.first()))
        return Result.success()
    }
}

object Notifications {
    fun ensureChannel(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val ch = NotificationChannel(CHANNEL_ID, context.getString(R.string.notification_channel), NotificationManager.IMPORTANCE_DEFAULT)
            context.getSystemService(NotificationManager::class.java).createNotificationChannel(ch)
        }
    }

    fun showDailyReminder(context: Context) {
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) return
        ensureChannel(context)
        val open = Intent(context, MainActivity::class.java).apply {
            putExtra(EXTRA_OPEN_CALL, true)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val pi = PendingIntent.getActivity(context, 1, open, PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val n = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle(context.getString(R.string.notification_title))
            .setContentText(context.getString(R.string.notification_text))
            .setContentIntent(pi)
            .setAutoCancel(true)
            .build()
        NotificationManagerCompat.from(context).notify(1001, n)
    }
}
