package `in`.kisancoldlink.app.domain

import `in`.kisancoldlink.app.Fixtures
import `in`.kisancoldlink.app.core.utils.Money
import `in`.kisancoldlink.app.core.utils.Units
import `in`.kisancoldlink.app.domain.model.AppLanguage
import `in`.kisancoldlink.app.domain.model.FarmerLot
import `in`.kisancoldlink.app.domain.repository.FarmerRepository
import `in`.kisancoldlink.app.domain.usecase.FarmerInput
import `in`.kisancoldlink.app.domain.usecase.IdentifyFarmerUseCase
import `in`.kisancoldlink.app.domain.usecase.IdentifyInputError
import `in`.kisancoldlink.app.notifications.ReminderScheduler
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.LocalDateTime

class DomainTest {
    @Test fun indianRupeeGrouping() {
        assertEquals("1,17,389", Money.inr(117389.4))
        assertEquals("999", Money.inr(999.0))
        assertEquals("12,34,56,789", Money.inr(123456789.0))
        assertEquals("2,500", Money.inr(-2500.0)) // sign is said as "loss", never "-"
    }

    @Test fun quintalKgConversion() {
        assertEquals(5000.0, Units.quintalsToKg(50.0), 0.0)
        assertEquals(0.5, Units.kgToQuintals(50.0), 0.0)
        assertEquals(23.89, Units.perQuintalToPerKg(2389.0), 1e-9)
        assertEquals("23.89", Money.perKg(2389.0))
        assertEquals("24", Money.perKg(2400.0))
    }

    @Test fun phoneValidation() {
        assertEquals("9848012345", FarmerInput.normalizePhone("+91 98480-12345"))
        assertEquals(null, FarmerInput.validate("Ramu", "9848012345"))
        assertEquals(IdentifyInputError.NAME_REQUIRED, FarmerInput.validate("  ", "9848012345"))
        assertEquals(IdentifyInputError.PHONE_INVALID, FarmerInput.validate("Ramu", "98480"))
        assertEquals(IdentifyInputError.PHONE_INVALID, FarmerInput.validate("Ramu", "1234567890123456"))
    }

    private class CountingFarmers : FarmerRepository {
        var calls = 0
        override suspend fun identify(name: String, phone: String): Result<List<FarmerLot>> { calls++; return Result.success(emptyList()) }
    }

    @Test fun invalidInputNeverReachesBackend() = runTest {
        val repo = CountingFarmers()
        val r = IdentifyFarmerUseCase(repo)("", "123")
        assertTrue(r is IdentifyFarmerUseCase.Outcome.Invalid)
        assertEquals(0, repo.calls)
        IdentifyFarmerUseCase(repo)("Ramu", "+91 98480 12345")
        assertEquals(1, repo.calls)
    }

    @Test fun fixtureMapsBackendFiguresWithoutRecalculating() {
        val d = Fixtures.lotView().toDomain()
        assertEquals("Paddy (Dhan)(Common)", d.lot.commodity)
        assertEquals("వరి", d.lot.crop(AppLanguage.TELUGU)) // crop comes from the admin lot, not hardcoded
        val rec = d.recommendation!!
        val best = d.mandis.first { it.market == rec.market }
        assertEquals(best.best!!.netRevenue, rec.option.netRevenue, 0.0)
        // Ranking is the backend's: the recommendation has the highest net receipts of all available options.
        val maxNet = d.mandis.filter { it.available }.flatMap { it.options }.maxOf { it.netRevenue }
        assertEquals(maxNet, rec.option.netRevenue, 0.0)
        // Net = gross - transport - commission - storage, exactly as the planner computed it.
        val now = best.sellNow!!
        assertEquals(now.grossValue - now.transportCost - now.marketFee - now.storageCost, now.netRevenue, 1.0)
        assertTrue(d.market.values.none { it.live }) // stored data is never labelled live
    }

    @Test fun reminderDelay() {
        val now = LocalDateTime.of(2026, 11, 12, 8, 30)
        assertEquals(22 * 60 + 30L, ReminderScheduler.delayUntil(now, 7, 0).toMinutes())
        assertEquals(30L, ReminderScheduler.delayUntil(now, 9, 0).toMinutes())
    }
}
