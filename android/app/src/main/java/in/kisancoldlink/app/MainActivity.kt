package `in`.kisancoldlink.app

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import dagger.hilt.android.AndroidEntryPoint
import `in`.kisancoldlink.app.core.design.KclColors
import `in`.kisancoldlink.app.core.design.KisanTheme
import `in`.kisancoldlink.app.core.utils.ProvideLanguage
import `in`.kisancoldlink.app.navigation.AppNavigation
import `in`.kisancoldlink.app.navigation.RootViewModel
import `in`.kisancoldlink.app.notifications.EXTRA_OPEN_CALL

/** Hosts navigation only; every screen lives in features/. */
@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    private val root: RootViewModel by viewModels()
    private var openCall by mutableStateOf(false)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        openCall = intent?.getBooleanExtra(EXTRA_OPEN_CALL, false) == true
        setContent {
            val language by root.language.collectAsStateWithLifecycle()
            val start by root.startRoute.collectAsStateWithLifecycle()
            ProvideLanguage(language) {
                KisanTheme {
                    Box(Modifier.fillMaxSize().background(KclColors.Cream)) {
                        start?.let { AppNavigation(it, openCall, onCallOpened = { openCall = false }) }
                    }
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        if (intent.getBooleanExtra(EXTRA_OPEN_CALL, false)) openCall = true
    }
}
