package `in`.kisancoldlink.app

import android.app.Application
import dagger.hilt.android.HiltAndroidApp
import `in`.kisancoldlink.app.notifications.Notifications

@HiltAndroidApp
class KisanApp : Application() {
    override fun onCreate() {
        super.onCreate()
        Notifications.ensureChannel(this)
    }
}
