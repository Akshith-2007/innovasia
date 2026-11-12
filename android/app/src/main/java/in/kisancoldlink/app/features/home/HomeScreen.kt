package `in`.kisancoldlink.app.features.home

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Call
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import `in`.kisancoldlink.app.R
import `in`.kisancoldlink.app.core.design.BigButton
import `in`.kisancoldlink.app.core.design.KclCard
import `in`.kisancoldlink.app.core.design.KclColors
import `in`.kisancoldlink.app.core.design.KeyValue
import `in`.kisancoldlink.app.core.design.LoadingBox
import `in`.kisancoldlink.app.core.design.MessageBox
import `in`.kisancoldlink.app.core.design.Pill
import `in`.kisancoldlink.app.core.design.RaithannaAvatar
import `in`.kisancoldlink.app.core.design.SectionTitle
import `in`.kisancoldlink.app.core.utils.Dates
import `in`.kisancoldlink.app.core.utils.Money
import `in`.kisancoldlink.app.core.utils.Numbers
import `in`.kisancoldlink.app.core.utils.Units
import `in`.kisancoldlink.app.domain.model.AppLanguage
import `in`.kisancoldlink.app.domain.model.LotDetail
import `in`.kisancoldlink.app.domain.model.MarketSnapshot
import `in`.kisancoldlink.app.features.call.errorText
import `in`.kisancoldlink.app.features.lot.LotDetailViewModel
import `in`.kisancoldlink.app.features.lot.LotUiState
import java.text.DateFormat
import java.util.Date

@Composable
fun HomeScreen(onCall: () -> Unit, viewModel: LotDetailViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    HomeContent(state, onCall, viewModel::refresh)
}

/** Loading / error / content wrapper shared by the lot screens. */
@Composable
fun LotScaffold(state: LotUiState, onRetry: () -> Unit, content: @Composable ColumnScope.(LotDetail) -> Unit) {
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 18.dp, vertical = 16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        val result = state.result
        when {
            state.loading && result == null -> LoadingBox(stringResource(R.string.loading))
            result == null -> MessageBox(errorText(state.error), action = stringResource(R.string.retry), onAction = onRetry,
                modifier = Modifier.testTag("lot_error"))
            else -> {
                if (result.fromCache) {
                    // Saved copy: labelled with its date, never presented as live.
                    MessageBox(stringResource(R.string.cached_notice, formatTime(result.fetchedAtMillis)), isError = false,
                        action = stringResource(R.string.refresh), onAction = onRetry, modifier = Modifier.testTag("cached_notice"))
                }
                content(result.detail)
            }
        }
    }
}

@Composable
fun HomeContent(state: LotUiState, onCall: () -> Unit, onRetry: () -> Unit) {
    LotScaffold(state, onRetry) { detail ->
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            RaithannaAvatar(72.dp, description = stringResource(R.string.assistant_name))
            Column {
                // Always "Babai", never the registered name.
                Text(stringResource(R.string.greeting_babai), style = MaterialTheme.typography.headlineMedium, color = KclColors.ForestDeep,
                    modifier = Modifier.testTag("greeting"))
                Text(stringResource(R.string.brand_tagline), style = MaterialTheme.typography.bodySmall, color = KclColors.Muted)
            }
        }
        LotCard(detail, state.language)
        TodaysMarket(detail)
        RecommendationCard(detail)
        BigButton(stringResource(R.string.talk_to_raithanna), onCall, icon = Icons.Filled.Call, container = KclColors.Amber,
            content = KclColors.Ink, modifier = Modifier.testTag("talk"))
    }
}

@Composable
fun LotCard(detail: LotDetail, language: AppLanguage) {
    val lot = detail.lot
    KclCard(Modifier.testTag("lot_card")) {
        SectionTitle(stringResource(R.string.my_crop_lot))
        Text(lot.crop(language), style = MaterialTheme.typography.displaySmall, color = KclColors.Forest, modifier = Modifier.testTag("crop_name"))
        KeyValue(stringResource(R.string.quantity_label),
            stringResource(R.string.quantity_value, Numbers.plain(lot.quantityQuintals), Numbers.plain(Units.quintalsToKg(lot.quantityQuintals))))
        lot.village?.let { KeyValue(stringResource(R.string.village_label), it) }
        KeyValue(stringResource(R.string.storage_label), storageLabel(lot.storageOption))
        KeyValue(stringResource(R.string.lot_status), stringResource(R.string.lot_status_registered))
    }
}

@Composable
fun storageLabel(id: String): String = stringResource(
    when (id) {
        "home_ambient" -> R.string.storage_home_ambient
        "zecc" -> R.string.storage_zecc
        "onion_ventilated" -> R.string.storage_onion_ventilated
        "cold_storage" -> R.string.storage_cold_storage
        "warehouse" -> R.string.storage_warehouse
        else -> R.string.storage_none
    },
)

@Composable
fun TodaysMarket(detail: LotDetail) {
    val mandi = detail.headlineMandi ?: return
    val snap = detail.market[mandi.market] ?: mandi.latestModal?.let {
        MarketSnapshot(mandi.market, mandi.latestDate.orEmpty(), null, null, it, live = false, fromMirror = false)
    } ?: return
    MarketSnapshotCard(snap, detail.sourceThirdParty)
}

@Composable
fun MarketSnapshotCard(snap: MarketSnapshot, mirror: Boolean, modifier: Modifier = Modifier) {
    val locale = LocalConfiguration.current.locales[0]
    KclCard(modifier.testTag("market_card")) {
        SectionTitle(stringResource(R.string.todays_market))
        Text(snap.market, style = MaterialTheme.typography.titleLarge, color = KclColors.ForestDeep)
        KeyValue(stringResource(R.string.modal_price), stringResource(R.string.per_quintal, Money.inr(snap.modalPrice)), bold = true)
        KeyValue(stringResource(R.string.per_kg_label), stringResource(R.string.per_kg, Money.perKg(snap.modalPrice)))
        snap.minPrice?.let { KeyValue(stringResource(R.string.min_price), stringResource(R.string.per_quintal, Money.inr(it))) }
        snap.maxPrice?.let { KeyValue(stringResource(R.string.max_price), stringResource(R.string.per_quintal, Money.inr(it))) }
        Text(stringResource(R.string.observed_on, Dates.display(snap.date, locale)), style = MaterialTheme.typography.bodyMedium)
        Pill(stringResource(if (snap.live) R.string.source_live else R.string.source_stored),
            if (snap.live) KclColors.Sage else KclColors.DangerSoft, if (snap.live) KclColors.ForestDeep else KclColors.Danger)
        if (mirror || snap.fromMirror) Text(stringResource(R.string.source_mirror), style = MaterialTheme.typography.bodySmall, color = KclColors.Muted)
    }
}

@Composable
fun RecommendationCard(detail: LotDetail) {
    KclCard(Modifier.testTag("recommendation"), tint = KclColors.Sage) {
        SectionTitle(stringResource(R.string.recommendation))
        val rec = detail.recommendation
        if (rec == null) {
            Text(stringResource(R.string.rec_none), style = MaterialTheme.typography.bodyLarge)
            return@KclCard
        }
        val o = rec.option
        Text(
            if (o.days == 0) stringResource(R.string.rec_sell_now, rec.market) else stringResource(R.string.rec_store, o.days, rec.market),
            style = MaterialTheme.typography.titleLarge, color = KclColors.ForestDeep,
        )
        Text(
            if (o.isLoss) stringResource(R.string.rec_loss, Money.inr(o.netRevenue)) else stringResource(R.string.rec_net, Money.inr(o.netRevenue)),
            style = MaterialTheme.typography.bodyLarge, color = if (o.isLoss) KclColors.Danger else KclColors.Forest,
        )
        Text(stringResource(R.string.rec_decision), style = MaterialTheme.typography.bodyMedium, color = KclColors.Muted)
    }
}

fun formatTime(millis: Long): String = DateFormat.getDateTimeInstance(DateFormat.MEDIUM, DateFormat.SHORT).format(Date(millis))
