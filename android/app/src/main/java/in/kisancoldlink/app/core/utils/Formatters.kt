package `in`.kisancoldlink.app.core.utils

import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Locale
import kotlin.math.abs
import kotlin.math.roundToLong

/** 1 quintal = 100 kg. Prices from AGMARKNET are INR per quintal. */
object Units {
    const val KG_PER_QUINTAL = 100.0
    fun quintalsToKg(quintals: Double): Double = quintals * KG_PER_QUINTAL
    fun kgToQuintals(kg: Double): Double = kg / KG_PER_QUINTAL
    fun perQuintalToPerKg(pricePerQuintal: Double): Double = pricePerQuintal / KG_PER_QUINTAL
}

object Money {
    /** Whole rupees with Indian grouping, e.g. 117389.4 -> "1,17,389". Sign is dropped; callers say "loss". */
    fun inr(value: Double): String {
        val s = abs(value).roundToLong().toString()
        if (s.length <= 3) return s
        val head = s.dropLast(3)
        val tail = s.takeLast(3)
        val groups = head.reversed().chunked(2).joinToString(",").reversed()
        return "$groups,$tail"
    }

    /** Price per kg with up to two decimals ("23.89"). */
    fun perKg(pricePerQuintal: Double): String =
        String.format(Locale.US, "%.2f", Units.perQuintalToPerKg(pricePerQuintal)).trimEnd('0').trimEnd('.')
}

object Numbers {
    fun plain(v: Double): String = if (v == v.toLong().toDouble()) v.toLong().toString() else String.format(Locale.US, "%.2f", v).trimEnd('0').trimEnd('.')
}

object Dates {
    fun display(iso: String?, locale: Locale): String {
        if (iso.isNullOrBlank()) return "—"
        return runCatching { LocalDate.parse(iso.take(10)).format(DateTimeFormatter.ofPattern("d MMM yyyy", locale)) }.getOrDefault(iso)
    }
}
