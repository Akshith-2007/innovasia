package `in`.kisancoldlink.app.data.dto

import `in`.kisancoldlink.app.domain.model.FarmerLot
import `in`.kisancoldlink.app.domain.model.HorizonUnavailable
import `in`.kisancoldlink.app.domain.model.LivePrice
import `in`.kisancoldlink.app.domain.model.LotDetail
import `in`.kisancoldlink.app.domain.model.LotInfo
import `in`.kisancoldlink.app.domain.model.MandiResult
import `in`.kisancoldlink.app.domain.model.MarketSnapshot
import `in`.kisancoldlink.app.domain.model.Recommendation
import `in`.kisancoldlink.app.domain.model.SaleOption
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// Shapes mirror backend/app/api/mobile.py and backend/app/services/{mobile,lot}_service.py exactly.

@Serializable
data class EnvelopeDto<T>(val data: T, val meta: Map<String, kotlinx.serialization.json.JsonElement> = emptyMap())

@Serializable
data class IdentifyRequestDto(val name: String, val phone: String)

@Serializable
data class AdvisoryRequestDto(val stage: String, val language: String, val audio: Boolean = true)

@Serializable
data class LotSummaryDto(
    @SerialName("lot_id") val lotId: String,
    @SerialName("farmer_name") val farmerName: String,
    val village: String? = null,
    val state: String,
    val district: String? = null,
    val commodity: String,
    @SerialName("crop_te") val cropTe: String,
    @SerialName("crop_en") val cropEn: String,
    @SerialName("quantity_quintals") val quantityQuintals: Double,
    @SerialName("storage_option") val storageOption: String = "sell_now",
    @SerialName("mandi_count") val mandiCount: Int = 0,
    val token: String = "",
) {
    fun toDomain() = FarmerLot(lotId, token, farmerName, village, state, district, commodity, cropTe, cropEn,
        quantityQuintals, storageOption, mandiCount)
}

@Serializable
data class LotDto(
    val id: String,
    @SerialName("farmer_name") val farmerName: String,
    val village: String? = null,
    val state: String,
    val district: String? = null,
    val commodity: String,
    @SerialName("quantity_quintals") val quantityQuintals: Double,
    @SerialName("transport_rate_per_quintal_km") val transportRate: Double,
    @SerialName("market_fee_pct") val marketFeePct: Double? = null,
    @SerialName("storage_option") val storageOption: String? = null,
)

@Serializable
data class ErrorDto(val code: String = "", val message: String = "")

@Serializable
data class ObservationDto(val date: String, @SerialName("modal_price") val modalPrice: Double)

@Serializable
data class OptionDto(
    val days: Int,
    @SerialName("price_per_quintal") val pricePerQuintal: Double,
    @SerialName("sellable_quintals") val sellableQuintals: Double,
    @SerialName("storage_cost") val storageCost: Double = 0.0,
    @SerialName("transport_cost") val transportCost: Double = 0.0,
    @SerialName("market_fee") val marketFee: Double = 0.0,
    @SerialName("net_revenue") val netRevenue: Double,
    val profit: Double? = null,
    @SerialName("vs_sell_now") val vsSellNow: Double? = null,
    @SerialName("forecast_test_mape") val forecastTestMape: Double? = null,
) {
    fun toDomain() = SaleOption(days, pricePerQuintal, sellableQuintals, transportCost, marketFee, storageCost,
        netRevenue, profit, vsSellNow, forecastTestMape)
}

@Serializable
data class HorizonDto(val days: Int, val reason: String = "")

@Serializable
data class StorageOptionDto(val id: String? = null, val name: String? = null)

@Serializable
data class MandiDto(
    val market: String,
    val district: String? = null,
    @SerialName("distance_km") val distanceKm: Double,
    @SerialName("transport_cost_per_quintal") val transportPerQuintal: Double = 0.0,
    val available: Boolean,
    val error: ErrorDto? = null,
    @SerialName("latest_observation") val latestObservation: ObservationDto? = null,
    val options: List<OptionDto> = emptyList(),
    val best: OptionDto? = null,
    @SerialName("unavailable_horizons") val unavailableHorizons: List<HorizonDto> = emptyList(),
    @SerialName("storage_option") val storageOption: StorageOptionDto? = null,
) {
    fun toDomain() = MandiResult(
        market, district, distanceKm, transportPerQuintal, available, error?.message,
        latestObservation?.date, latestObservation?.modalPrice, options.map { it.toDomain() }, best?.toDomain(),
        unavailableHorizons.map { HorizonUnavailable(it.days, it.reason) }, storageOption?.name,
    )
}

@Serializable
data class RecommendationDto(
    val market: String,
    @SerialName("distance_km") val distanceKm: Double,
    val option: OptionDto,
    @SerialName("margin_over_next_best") val marginOverNextBest: Double? = null,
)

@Serializable
data class ComparisonDto(
    val mandis: List<MandiDto>,
    val recommendation: RecommendationDto? = null,
    val assumptions: List<String> = emptyList(),
)

@Serializable
data class SnapshotDto(
    @SerialName("arrival_date") val arrivalDate: String,
    @SerialName("min_price") val minPrice: Double? = null,
    @SerialName("max_price") val maxPrice: Double? = null,
    @SerialName("modal_price") val modalPrice: Double,
    @SerialName("source_kind") val sourceKind: String? = null,
    val live: Boolean = false,
)

@Serializable
data class SourceDto(val live: Boolean = false, val cached: Boolean = true, @SerialName("third_party") val thirdParty: Boolean = false)

@Serializable
data class LotViewDto(
    val lot: LotDto,
    val summary: LotSummaryDto,
    val comparison: ComparisonDto,
    val market: Map<String, SnapshotDto> = emptyMap(),
    val source: SourceDto? = null,
) {
    fun toDomain() = LotDetail(
        lot = LotInfo(lot.id, lot.farmerName, lot.village, lot.state, lot.district, lot.commodity, summary.cropTe,
            summary.cropEn, lot.quantityQuintals, lot.transportRate, lot.marketFeePct, lot.storageOption ?: "sell_now"),
        mandis = comparison.mandis.map { it.toDomain() },
        recommendation = comparison.recommendation?.let { Recommendation(it.market, it.distanceKm, it.option.toDomain(), it.marginOverNextBest) },
        market = market.mapValues { (k, v) ->
            MarketSnapshot(k, v.arrivalDate, v.minPrice, v.maxPrice, v.modalPrice, v.live, v.sourceKind == "third_party_mirror")
        },
        sourceThirdParty = source?.thirdParty == true || market.values.any { it.sourceKind == "third_party_mirror" },
        assumptions = comparison.assumptions,
    )
}

@Serializable
data class AudioDto(val key: String, val voice: String = "", val path: String)

@Serializable
data class AdvisoryDto(
    val stage: String,
    val language: String,
    val script: String,
    val crop: String = "",
    val narration: String = "template",
    val audio: AudioDto? = null,
    @SerialName("tts_error") val ttsError: ErrorDto? = null,
)

@Serializable
data class PriceRecordDto(
    val market: String,
    @SerialName("arrival_date") val arrivalDate: String? = null,
    @SerialName("min_price") val minPrice: Double? = null,
    @SerialName("max_price") val maxPrice: Double? = null,
    @SerialName("modal_price") val modalPrice: Double,
)

@Serializable
data class LiveMarketDto(val records: List<PriceRecordDto> = emptyList(), val source: SourceDto? = null) {
    /** Live only when the backend says the values came from data.gov.in in this request window. */
    fun toDomain(): LivePrice? = records.maxByOrNull { it.arrivalDate ?: "" }?.let {
        LivePrice(it.market, it.arrivalDate ?: "", it.minPrice, it.maxPrice, it.modalPrice, source?.live == true)
    }
}
