package `in`.kisancoldlink.app.core.utils

import android.content.Context
import android.content.ContextWrapper
import android.content.res.Configuration
import android.content.res.Resources
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import `in`.kisancoldlink.app.domain.model.AppLanguage
import java.util.Locale

/**
 * Keeps the Activity as base context (Hilt ViewModels, permission launchers need it) but serves
 * resources for the chosen language, so stringResource() picks values-te or values.
 */
class LocalizedContext(base: Context, private val localized: Resources) : ContextWrapper(base) {
    override fun getResources(): Resources = localized
}

fun AppLanguage.locale(): Locale = Locale.forLanguageTag(if (this == AppLanguage.TELUGU) "te-IN" else "en-IN")

fun Context.localized(language: AppLanguage): Context {
    val config = Configuration(resources.configuration).apply { setLocale(language.locale()) }
    return LocalizedContext(this, createConfigurationContext(config).resources)
}

@Composable
fun ProvideLanguage(language: AppLanguage, content: @Composable () -> Unit) {
    val base = LocalContext.current
    val parent = LocalConfiguration.current
    val config = remember(language, parent) { Configuration(parent).apply { setLocale(language.locale()) } }
    val context = remember(language, base, config) { LocalizedContext(base, base.createConfigurationContext(config).resources) }
    CompositionLocalProvider(LocalContext provides context, LocalConfiguration provides config, content = content)
}
