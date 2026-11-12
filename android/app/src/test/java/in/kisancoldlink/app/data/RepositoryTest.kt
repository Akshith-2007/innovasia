package `in`.kisancoldlink.app.data

import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import `in`.kisancoldlink.app.Fixtures
import `in`.kisancoldlink.app.core.networking.AppError
import `in`.kisancoldlink.app.data.local.LocalFiles
import `in`.kisancoldlink.app.data.remote.KisanApi
import `in`.kisancoldlink.app.data.repository.Clock
import `in`.kisancoldlink.app.data.repository.RemoteAdvisoryRepository
import `in`.kisancoldlink.app.data.repository.RemoteFarmerRepository
import `in`.kisancoldlink.app.data.repository.RemoteLotRepository
import `in`.kisancoldlink.app.di.NetworkModule
import `in`.kisancoldlink.app.domain.model.AdvisoryStage
import `in`.kisancoldlink.app.domain.model.AppLanguage
import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okio.Buffer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import okhttp3.MediaType.Companion.toMediaType

@RunWith(AndroidJUnit4::class)
class RepositoryTest {
    private val server = MockWebServer()
    private lateinit var api: KisanApi
    private lateinit var files: LocalFiles
    private var now = 1_000L
    private val clock = Clock { now }

    @Before fun setUp() {
        server.start()
        val json = NetworkModule.json()
        api = Retrofit.Builder().baseUrl(server.url("/api/v1/")).client(NetworkModule.okHttp())
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType())).build().create(KisanApi::class.java)
        files = LocalFiles(ApplicationProvider.getApplicationContext(), json)
    }

    @After fun tearDown() = server.shutdown()

    private fun ok(name: String) = MockResponse().setBody(Fixtures.text(name))

    @Test fun identifyParsesLotsAndSendsNormalisedRequest() = runBlocking {
        server.enqueue(ok("identify"))
        val lots = RemoteFarmerRepository(api).identify("E2E Test (sample inputs)", "9000000000").getOrThrow()
        assertEquals(1, lots.size)
        assertEquals("వరి", lots[0].cropTe)
        assertEquals("fixture-token", lots[0].token)
        val req = server.takeRequest()
        assertEquals("/api/v1/mobile/identify", req.path)
        assertTrue(req.body.readUtf8().contains("\"phone\":\"9000000000\""))
    }

    @Test fun notRegisteredMapsToTheBriefMessage() = runBlocking {
        server.enqueue(ok("not_registered").setResponseCode(404))
        val err = RemoteFarmerRepository(api).identify("Nobody", "9999999999").exceptionOrNull()
        assertTrue(err is AppError.NotRegistered)
        assertEquals("బాబాయ్, మీ వివరాలు ఇంకా నమోదు కాలేదు. దయచేసి మా నిర్వాహకులను సంప్రదించండి.", err!!.message)
    }

    @Test fun lotSendsTokenAndFallsBackToLabelledCacheWhenOffline() = runBlocking {
        val repo = RemoteLotRepository(api, files, clock)
        server.enqueue(ok("lot_view"))
        val fresh = repo.lotDetail(Fixtures.session).getOrThrow()
        assertFalse(fresh.fromCache)
        assertEquals("token", server.takeRequest().getHeader("X-Farmer-Token"))

        server.shutdown() // backend unreachable
        now += RemoteLotRepository.MEMORY_TTL_MS + 1
        val cached = repo.lotDetail(Fixtures.session, forceRefresh = true).getOrThrow()
        assertTrue(cached.fromCache)
        assertEquals(1_000L, cached.fetchedAtMillis) // shown with its original time, never as new
        assertEquals(fresh.detail.recommendation, cached.detail.recommendation)
    }

    @Test fun revokedLotDoesNotShowCachedData() = runBlocking {
        val repo = RemoteLotRepository(api, files, clock)
        server.enqueue(ok("lot_view")); repo.lotDetail(Fixtures.session).getOrThrow()
        server.enqueue(MockResponse().setResponseCode(401).setBody("""{"error":{"code":"unauthorized","message":"This lot is not available."}}"""))
        val r = repo.lotDetail(Fixtures.session, forceRefresh = true)
        assertTrue(r.exceptionOrNull() is AppError.Unauthorized)
    }

    @Test fun advisoryDownloadsAudioOnceAndCachesReport() = runBlocking {
        val repo = RemoteAdvisoryRepository(api, files, clock)
        val withAudio = Fixtures.text("advisory_report_te")
            .replace("\"audio\": null", "\"audio\": {\"key\": \"${"a".repeat(40)}\", \"voice\": \"te-IN-MohanNeural\", \"path\": \"/mobile/lots/lot1/audio/${"a".repeat(40)}\"}")
            .replace(Regex("\"tts_error\": \\{[^}]*\\}"), "\"tts_error\": null")
        server.enqueue(MockResponse().setBody(withAudio))
        server.enqueue(MockResponse().setBody(Buffer().write(byteArrayOf(0x49, 0x44, 0x33, 1, 2, 3))))
        val a = repo.prepare(Fixtures.session, AdvisoryStage.REPORT, AppLanguage.TELUGU).getOrThrow()
        assertNotNull(a.audioFile)
        assertNull(a.audioProblem)
        server.takeRequest()
        val audioReq = server.takeRequest()
        assertEquals("/api/v1/mobile/lots/lot1/audio/${"a".repeat(40)}", audioReq.path) // relative to /api/v1, not host root
        assertEquals("token", audioReq.getHeader("X-Farmer-Token"))

        server.enqueue(MockResponse().setBody(withAudio))
        repo.prepare(Fixtures.session, AdvisoryStage.REPORT, AppLanguage.TELUGU).getOrThrow()
        assertEquals(3, server.requestCount) // same key: audio not downloaded again

        val saved = repo.lastReport(Fixtures.session, AppLanguage.TELUGU)!!
        assertEquals(a.script, saved.script)
        assertNotNull(saved.audioFile)
    }

    @Test fun ttsFailureKeepsTextWithoutAudio() = runBlocking {
        server.enqueue(ok("advisory_greeting_te"))
        val a = RemoteAdvisoryRepository(api, files, clock).prepare(Fixtures.session, AdvisoryStage.GREETING, AppLanguage.TELUGU).getOrThrow()
        assertNull(a.audioFile)
        assertNotNull(a.audioProblem)
        assertTrue(a.script.startsWith("బాబాయ్... శుభోదయం! నేను రైతన్నను మాట్లాడుతున్నాను."))
    }

    @Test fun backendDownIsANetworkError() = runBlocking {
        server.shutdown()
        val r = RemoteAdvisoryRepository(api, files, clock).prepare(Fixtures.session, AdvisoryStage.GREETING, AppLanguage.TELUGU)
        assertTrue(r.exceptionOrNull() is AppError.Network)
    }
}
