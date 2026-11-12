package `in`.kisancoldlink.app.features.market

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import `in`.kisancoldlink.app.R
import `in`.kisancoldlink.app.core.design.KclColors
import `in`.kisancoldlink.app.core.design.LoadingBox
import `in`.kisancoldlink.app.core.design.MessageBox
import `in`.kisancoldlink.app.core.design.SecondaryButton
import `in`.kisancoldlink.app.core.design.SectionTitle
import `in`.kisancoldlink.app.domain.model.MarketSnapshot
import `in`.kisancoldlink.app.features.call.errorText
import `in`.kisancoldlink.app.features.home.LotScaffold
import `in`.kisancoldlink.app.features.home.MarketSnapshotCard
import `in`.kisancoldlink.app.features.lot.LiveState
import `in`.kisancoldlink.app.features.lot.LotDetailViewModel
import `in`.kisancoldlink.app.features.mandi.MandiComparisonCard

@Composable
fun MarketScreen(viewModel: LotDetailViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    LotScaffold(state, viewModel::refresh) { detail ->
        SectionTitle(stringResource(R.string.market_title))
        detail.mandis.filter { it.available }.forEach { m ->
            detail.market[m.market]?.let { MarketSnapshotCard(it, detail.sourceThirdParty) }
            when (val live = state.live[m.market]) {
                null -> SecondaryButton(stringResource(R.string.check_live), { viewModel.checkLive(m.market) },
                    modifier = Modifier.testTag("live_${m.market}"))
                LiveState.Loading -> LoadingBox(stringResource(R.string.loading))
                is LiveState.Failed -> MessageBox(errorText(live.error), action = stringResource(R.string.retry), onAction = { viewModel.checkLive(m.market) })
                is LiveState.Loaded -> live.price?.let {
                    // The backend labels whether this came from data.gov.in today or from stored data.
                    MarketSnapshotCard(MarketSnapshot(it.market, it.date, it.minPrice, it.maxPrice, it.modalPrice, it.live, false), mirror = false)
                } ?: Text(stringResource(R.string.live_none), style = MaterialTheme.typography.bodyMedium, color = KclColors.Muted)
            }
        }
        SectionTitle(stringResource(R.string.mandi_comparison))
        detail.mandis.forEach { MandiComparisonCard(it, it.market == detail.recommendation?.market, detail.lot.marketFeePct != null) }
    }
}
