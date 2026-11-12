package `in`.kisancoldlink.app.features.storage

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import `in`.kisancoldlink.app.R
import `in`.kisancoldlink.app.core.design.KclCard
import `in`.kisancoldlink.app.core.design.KclColors
import `in`.kisancoldlink.app.core.design.KeyValue
import `in`.kisancoldlink.app.core.design.SectionTitle
import `in`.kisancoldlink.app.core.utils.Money
import `in`.kisancoldlink.app.core.utils.Numbers
import `in`.kisancoldlink.app.domain.model.MandiResult
import `in`.kisancoldlink.app.features.mandi.NetLine
import java.util.Locale

/** Sell now vs the storage periods the backend allowed (shelf life + evaluated forecasts only). */
@Composable
fun StorageComparison(mandi: MandiResult, modifier: Modifier = Modifier) {
    Column(modifier.testTag("storage_comparison"), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        SectionTitle(stringResource(R.string.storage_title))
        mandi.options.forEach { o ->
            KclCard(tint = if (mandi.best?.days == o.days) KclColors.Sage else KclColors.White) {
                Text(if (o.days == 0) stringResource(R.string.sell_now) else stringResource(R.string.store_days, o.days),
                    style = MaterialTheme.typography.titleMedium, color = KclColors.ForestDeep)
                KeyValue(stringResource(if (o.isForecast) R.string.forecast_price else R.string.modal_price),
                    stringResource(R.string.per_quintal, Money.inr(o.pricePerQuintal)))
                if (o.isForecast) {
                    KeyValue(stringResource(R.string.storage_cost), "− ₹" + Money.inr(o.storageCost))
                    Text(stringResource(R.string.sellable, Numbers.plain(Math.round(o.sellableQuintals * 100) / 100.0)),
                        style = MaterialTheme.typography.bodyMedium, color = KclColors.Muted)
                }
                KeyValue(stringResource(R.string.transport), "− ₹" + Money.inr(o.transportCost))
                HorizontalDivider(color = KclColors.Line)
                NetLine(o.netRevenue)
                o.forecastMapePct?.let {
                    Text(stringResource(R.string.forecast_note, String.format(Locale.US, "%.0f", it)),
                        style = MaterialTheme.typography.bodySmall, color = KclColors.AmberInk)
                }
            }
        }
        mandi.unavailableHorizons.forEach {
            Text(stringResource(R.string.horizon_unavailable, it.days, it.reason), style = MaterialTheme.typography.bodySmall, color = KclColors.Muted)
        }
    }
}
