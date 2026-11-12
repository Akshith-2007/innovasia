package `in`.kisancoldlink.app.navigation

import androidx.annotation.StringRes
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Agriculture
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.RecordVoiceOver
import androidx.compose.material.icons.filled.Storefront
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import `in`.kisancoldlink.app.R
import `in`.kisancoldlink.app.core.design.KclColors
import `in`.kisancoldlink.app.features.advisory.AnalysisScreen
import `in`.kisancoldlink.app.features.advisory.RaithannaScreen
import `in`.kisancoldlink.app.features.authentication.AuthScreen
import `in`.kisancoldlink.app.features.call.CallScreen
import `in`.kisancoldlink.app.features.home.HomeScreen
import `in`.kisancoldlink.app.features.lot.MyLotScreen
import `in`.kisancoldlink.app.features.market.MarketScreen
import `in`.kisancoldlink.app.features.onboarding.WelcomeScreen
import `in`.kisancoldlink.app.features.settings.ProfileScreen

object Routes {
    const val WELCOME = "welcome"
    const val AUTH = "auth"
    const val HOME = "home"
    const val MARKET = "market"
    const val LOT = "lot"
    const val RAITHANNA = "raithanna"
    const val PROFILE = "profile"
    const val CALL = "call"
    const val ANALYSIS = "analysis"
}

private data class Tab(val route: String, @StringRes val label: Int, val icon: ImageVector)

private val TABS = listOf(
    Tab(Routes.HOME, R.string.nav_home, Icons.Filled.Home),
    Tab(Routes.MARKET, R.string.nav_market, Icons.Filled.Storefront),
    Tab(Routes.LOT, R.string.nav_lot, Icons.Filled.Agriculture),
    Tab(Routes.RAITHANNA, R.string.nav_raithanna, Icons.Filled.RecordVoiceOver),
    Tab(Routes.PROFILE, R.string.nav_profile, Icons.Filled.Person),
)

@Composable
fun AppNavigation(startRoute: String, openCall: Boolean, onCallOpened: () -> Unit, nav: NavHostController = rememberNavController()) {
    val entry by nav.currentBackStackEntryAsState()
    val route = entry?.destination?.route
    LaunchedEffect(openCall, startRoute) {
        if (openCall && startRoute == Routes.HOME) {
            nav.navigate(Routes.CALL) { launchSingleTop = true }
            onCallOpened()
        }
    }
    Scaffold(
        containerColor = KclColors.Cream,
        bottomBar = {
            if (route in TABS.map { it.route }) NavigationBar(containerColor = KclColors.White) {
                TABS.forEach { tab ->
                    NavigationBarItem(
                        selected = route == tab.route,
                        onClick = {
                            nav.navigate(tab.route) {
                                popUpTo(nav.graph.findStartDestination().id) { saveState = true }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                        icon = { Icon(tab.icon, contentDescription = null) },
                        label = { Text(stringResource(tab.label)) },
                        colors = NavigationBarItemDefaults.colors(selectedIconColor = KclColors.Forest, indicatorColor = KclColors.Sage),
                    )
                }
            }
        },
    ) { padding ->
        val toHome: () -> Unit = { nav.navigate(Routes.HOME) { popUpTo(0) { inclusive = true } } }
        NavHost(nav, startDestination = startRoute, modifier = Modifier.padding(padding)) {
            composable(Routes.WELCOME) { WelcomeScreen(onContinue = { nav.navigate(Routes.AUTH) { popUpTo(Routes.WELCOME) { inclusive = true } } }) }
            composable(Routes.AUTH) { AuthScreen(onDone = toHome) }
            composable(Routes.HOME) { HomeScreen(onCall = { nav.navigate(Routes.CALL) }) }
            composable(Routes.MARKET) { MarketScreen() }
            composable(Routes.LOT) { MyLotScreen() }
            composable(Routes.RAITHANNA) { RaithannaScreen(onCall = { nav.navigate(Routes.CALL) }, onAnalysis = { nav.navigate(Routes.ANALYSIS) }) }
            composable(Routes.PROFILE) { ProfileScreen(onSignedOut = { nav.navigate(Routes.AUTH) { popUpTo(0) { inclusive = true } } }) }
            composable(Routes.CALL) {
                CallScreen(
                    onFinished = { if (!nav.popBackStack(Routes.HOME, inclusive = false)) toHome() },
                    onOpenAnalysis = { nav.navigate(Routes.ANALYSIS) },
                )
            }
            composable(Routes.ANALYSIS) { AnalysisScreen(onBack = { if (!nav.popBackStack()) toHome() }) }
        }
    }
}
