package `in`.kisancoldlink.app.features.mandi

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import `in`.kisancoldlink.app.R
import `in`.kisancoldlink.app.core.design.KclCard
import `in`.kisancoldlink.app.core.design.KclColors
import `in`.kisancoldlink.app.core.design.KeyValue
import `in`.kisancoldlink.app.core.design.Pill
import `in`.kisancoldlink.app.core.utils.Money
import `in`.kisancoldlink.app.core.utils.Numbers
import `in`.kisancoldlink.app.domain.model.MandiResult

/**
 * Selling now at one mandi: sale value - transport - commission - (unrecorded costs shown as such) = what is left.
 * All values were calculated on the backend; this only displays them.
 */
@Composable
fun MandiComparisonCard(mandi: MandiResult, isBest: Boolean, commissionRecorded: Boolean, modifier: Modifier = Modifier) {
    KclCard(modifier.testTag("mandi_${mandi.market}"), tint = if (isBest) KclColors.Sage else KclColors.White) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Text(mandi.market, style = MaterialTheme.typography.titleLarge, color = KclColors.ForestDeep, modifier = Modifier.weight(1f))
            if (isBest) Pill(stringResource(R.string.best_badge), KclColors.Amber, KclColors.Ink)
        }
        Text(stringResource(R.string.distance_km, Numbers.plain(mandi.distanceKm)), style = MaterialTheme.typography.bodyMedium, color = KclColors.Muted)
        val now = mandi.sellNow
        if (!mandi.available || now == null) {
            Text(stringResource(R.string.no_figure, mandi.unavailableReason ?: ""), style = MaterialTheme.typography.bodyMedium, color = KclColors.Danger)
            return@KclCard
        }
        KeyValue(stringResource(R.string.modal_price), stringResource(R.string.per_quintal, Money.inr(now.pricePerQuintal)))
        KeyValue(stringResource(R.string.gross_value), "₹" + Money.inr(now.grossValue))
        KeyValue(stringResource(R.string.transport), "− ₹" + Money.inr(now.transportCost))
        KeyValue(stringResource(R.string.commission),
            if (commissionRecorded) "− ₹" + Money.inr(now.marketFee) else stringResource(R.string.commission_missing))
        KeyValue(stringResource(R.string.loading_unloading), stringResource(R.string.not_recorded))
        HorizontalDivider(color = KclColors.Line)
        NetLine(now.netRevenue)
    }
}

@Composable
fun NetLine(net: Double) {
    if (net < 0) KeyValue(stringResource(R.string.net_loss), "₹" + Money.inr(net), valueColor = KclColors.Danger, bold = true)
    else KeyValue(stringResource(R.string.net_earnings), "₹" + Money.inr(net), valueColor = KclColors.Forest, bold = true)
}
