package `in`.kisancoldlink.app.core.design

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

private val scheme = lightColorScheme(
    primary = KclColors.Forest,
    onPrimary = KclColors.White,
    primaryContainer = KclColors.Sage,
    onPrimaryContainer = KclColors.ForestDeep,
    secondary = KclColors.Amber,
    onSecondary = KclColors.Ink,
    background = KclColors.Cream,
    onBackground = KclColors.Ink,
    surface = KclColors.White,
    onSurface = KclColors.Ink,
    surfaceVariant = KclColors.Sage,
    onSurfaceVariant = KclColors.Muted,
    outline = KclColors.Line,
    error = KclColors.Danger,
    errorContainer = KclColors.DangerSoft,
)

/** Light, high-contrast theme only: the app is used outdoors in daylight. */
@Composable
fun KisanTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = scheme, typography = KclTypography, content = content)
}
