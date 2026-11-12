package `in`.kisancoldlink.app.features.lot

import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.res.stringResource
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import `in`.kisancoldlink.app.R
import `in`.kisancoldlink.app.core.design.KclCard
import `in`.kisancoldlink.app.core.design.KeyValue
import `in`.kisancoldlink.app.core.utils.Money
import `in`.kisancoldlink.app.core.utils.Numbers
import `in`.kisancoldlink.app.features.home.LotCard
import `in`.kisancoldlink.app.features.home.LotScaffold
import `in`.kisancoldlink.app.features.storage.StorageComparison

@Composable
fun MyLotScreen(viewModel: LotDetailViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    LotScaffold(state, viewModel::refresh) { detail ->
        LotCard(detail, state.language)
        KclCard {
            KeyValue(stringResource(R.string.transport), stringResource(R.string.transport_rate, Numbers.plain(detail.lot.transportRatePerQuintalKm)))
            KeyValue(stringResource(R.string.commission), detail.lot.marketFeePct?.let { "${Numbers.plain(it)}%" } ?: stringResource(R.string.commission_missing))
            detail.mandis.forEach { KeyValue(it.market, stringResource(R.string.distance_km, Numbers.plain(it.distanceKm)) +
                " · ₹" + Money.inr(it.transportPerQuintal) + "/q") }
        }
        detail.headlineMandi?.let { StorageComparison(it) }
    }
}
