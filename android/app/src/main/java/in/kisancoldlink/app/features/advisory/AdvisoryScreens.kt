package `in`.kisancoldlink.app.features.advisory

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Analytics
import androidx.compose.material.icons.filled.Call
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import `in`.kisancoldlink.app.R
import `in`.kisancoldlink.app.core.design.BigButton
import `in`.kisancoldlink.app.core.design.KclCard
import `in`.kisancoldlink.app.core.design.KclColors
import `in`.kisancoldlink.app.core.design.RaithannaAvatar
import `in`.kisancoldlink.app.core.design.SecondaryButton
import `in`.kisancoldlink.app.core.design.SectionTitle
import `in`.kisancoldlink.app.features.home.LotScaffold
import `in`.kisancoldlink.app.features.home.RecommendationCard
import `in`.kisancoldlink.app.features.lot.LotDetailViewModel
import `in`.kisancoldlink.app.features.mandi.MandiComparisonCard
import `in`.kisancoldlink.app.features.storage.StorageComparison

/** Raithanna tab: who Raithanna is, the call button and the last report. */
@Composable
fun RaithannaScreen(onCall: () -> Unit, onAnalysis: () -> Unit, viewModel: LotDetailViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
        horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        RaithannaAvatar(160.dp, description = stringResource(R.string.assistant_name))
        Text(stringResource(R.string.assistant_name), style = MaterialTheme.typography.displaySmall, color = KclColors.ForestDeep)
        Text(stringResource(R.string.raithanna_intro), style = MaterialTheme.typography.bodyLarge, color = KclColors.Muted, textAlign = TextAlign.Center)
        BigButton(stringResource(R.string.talk_to_raithanna), onCall, icon = Icons.Filled.Call, container = KclColors.Amber, content = KclColors.Ink)
        SecondaryButton(stringResource(R.string.view_analysis), onAnalysis, icon = Icons.Filled.Analytics)
        LastReport(state.lastReport?.script)
    }
}

@Composable
private fun LastReport(script: String?) {
    KclCard {
        SectionTitle(stringResource(R.string.saved_report))
        Text(script ?: stringResource(R.string.no_saved_report), style = MaterialTheme.typography.bodyLarge)
    }
}

/** Every figure behind Raithanna's words: per-mandi costs, storage options and the assumptions. */
@Composable
fun AnalysisScreen(onBack: () -> Unit, viewModel: LotDetailViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    LotScaffold(state, viewModel::refresh) { detail ->
        SecondaryButton(stringResource(R.string.return_home), onBack, icon = Icons.AutoMirrored.Filled.ArrowBack)
        Text(stringResource(R.string.analysis_title), style = MaterialTheme.typography.headlineMedium, color = KclColors.ForestDeep)
        RecommendationCard(detail)
        SectionTitle(stringResource(R.string.mandi_comparison))
        detail.mandis.forEach { MandiComparisonCard(it, it.market == detail.recommendation?.market, detail.lot.marketFeePct != null) }
        detail.headlineMandi?.let { StorageComparison(it) }
        KclCard {
            SectionTitle(stringResource(R.string.assumptions))
            detail.assumptions.forEach { Text("• $it", style = MaterialTheme.typography.bodyMedium) }
        }
        LastReport(state.lastReport?.script)
    }
}
