package `in`.kisancoldlink.app.domain.usecase

import `in`.kisancoldlink.app.domain.model.FarmerLot
import `in`.kisancoldlink.app.domain.repository.FarmerRepository
import javax.inject.Inject

/** Input problems found before calling the backend. */
enum class IdentifyInputError { NAME_REQUIRED, PHONE_INVALID }

object FarmerInput {
    /** Last 10 digits, matching the backend: "+91 98480-12345" -> "9848012345". */
    fun normalizePhone(raw: String): String = raw.filter(Char::isDigit).takeLast(10)

    fun validate(name: String, phone: String): IdentifyInputError? = when {
        name.isBlank() -> IdentifyInputError.NAME_REQUIRED
        normalizePhone(phone).length != 10 || tooManyDigits(phone) -> IdentifyInputError.PHONE_INVALID
        else -> null
    }

    // More than 12 digits (e.g. a pasted account number) is not a mobile number.
    private fun tooManyDigits(phone: String) = phone.count(Char::isDigit) > 12
}

class IdentifyFarmerUseCase @Inject constructor(private val farmers: FarmerRepository) {
    sealed interface Outcome {
        data class Invalid(val error: IdentifyInputError) : Outcome
        data class Found(val lots: List<FarmerLot>) : Outcome
        data class Failed(val error: Throwable) : Outcome
    }

    suspend operator fun invoke(name: String, phone: String): Outcome {
        FarmerInput.validate(name, phone)?.let { return Outcome.Invalid(it) }
        return farmers.identify(name.trim(), FarmerInput.normalizePhone(phone)).fold(
            onSuccess = { Outcome.Found(it) },
            onFailure = { Outcome.Failed(it) },
        )
    }
}
