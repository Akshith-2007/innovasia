package `in`.kisancoldlink.app.domain.model

import java.io.File

enum class AppLanguage(val code: String) {
    TELUGU("te"), ENGLISH("en");

    companion object {
        fun fromCode(code: String?): AppLanguage = entries.firstOrNull { it.code == code } ?: TELUGU
    }
}

/** What the phone remembers after identification: a lot reference and its access token, never the phone number. */
data class LotSession(val lotId: String, val token: String, val commodity: String, val cropTe: String, val cropEn: String) {
    fun crop(language: AppLanguage) = if (language == AppLanguage.TELUGU) cropTe else cropEn
}

/** An admin-created lot as returned by identification. */
data class FarmerLot(
    val lotId: String,
    val token: String,
    val farmerName: String,
    val village: String?,
    val state: String,
    val district: String?,
    val commodity: String,
    val cropTe: String,
    val cropEn: String,
    val quantityQuintals: Double,
    val storageOption: String,
    val mandiCount: Int,
) {
    fun toSession() = LotSession(lotId, token, commodity, cropTe, cropEn)
    fun crop(language: AppLanguage) = if (language == AppLanguage.TELUGU) cropTe else cropEn
}

/** One way to sell, with figures calculated by the backend (storage planner + forecasts). */
data class SaleOption(
    val days: Int,
    val pricePerQuintal: Double,
    val sellableQuintals: Double,
    val transportCost: Double,
    val marketFee: Double,
    val storageCost: Double,
    val netRevenue: Double,
    val profit: Double?,
    val vsSellNow: Double?,
    val forecastMapePct: Double?,
) {
    /** Sale value before costs. 1 quintal = 100 kg; price is per quintal. */
    val grossValue: Double get() = sellableQuintals * pricePerQuintal
    val isForecast: Boolean get() = days > 0
    val isLoss: Boolean get() = netRevenue < 0
}

data class HorizonUnavailable(val days: Int, val reason: String)

data class MandiResult(
    val market: String,
    val district: String?,
    val distanceKm: Double,
    val transportPerQuintal: Double,
    val available: Boolean,
    val unavailableReason: String?,
    val latestDate: String?,
    val latestModal: Double?,
    val options: List<SaleOption>,
    val best: SaleOption?,
    val unavailableHorizons: List<HorizonUnavailable>,
    val storageName: String?,
) {
    val sellNow: SaleOption? get() = options.firstOrNull { it.days == 0 }
}

data class Recommendation(val market: String, val distanceKm: Double, val option: SaleOption, val marginOverNextBest: Double?)

/** Latest observed price at a mandi. [live] is true only for prices fetched from data.gov.in today. */
data class MarketSnapshot(
    val market: String,
    val date: String,
    val minPrice: Double?,
    val maxPrice: Double?,
    val modalPrice: Double,
    val live: Boolean,
    val fromMirror: Boolean,
)

data class LotInfo(
    val id: String,
    val farmerName: String,
    val village: String?,
    val state: String,
    val district: String?,
    val commodity: String,
    val cropTe: String,
    val cropEn: String,
    val quantityQuintals: Double,
    val transportRatePerQuintalKm: Double,
    val marketFeePct: Double?,
    val storageOption: String,
) {
    fun crop(language: AppLanguage) = if (language == AppLanguage.TELUGU) cropTe else cropEn
}

data class LotDetail(
    val lot: LotInfo,
    val mandis: List<MandiResult>,
    val recommendation: Recommendation?,
    val market: Map<String, MarketSnapshot>,
    val sourceThirdParty: Boolean,
    val assumptions: List<String>,
) {
    /** Mandi to headline on the dashboard: the recommended one, else the first with data. */
    val headlineMandi: MandiResult? get() = mandis.firstOrNull { it.market == recommendation?.market } ?: mandis.firstOrNull { it.available }
}

data class LotDetailResult(val detail: LotDetail, val fromCache: Boolean, val fetchedAtMillis: Long)

enum class AdvisoryStage(val code: String) { GREETING("greeting"), REPORT("report"), GOODBYE("goodbye") }

data class Advisory(
    val stage: AdvisoryStage,
    val language: AppLanguage,
    val script: String,
    /** Local MP3 ready to play, or null when the backend could not produce audio. */
    val audioFile: File?,
    /** Why there is no audio (not configured, timeout, download failed). Text is still shown. */
    val audioProblem: String?,
    val aiNarrated: Boolean,
)

data class LivePrice(val market: String, val date: String, val minPrice: Double?, val maxPrice: Double?, val modalPrice: Double, val live: Boolean)
