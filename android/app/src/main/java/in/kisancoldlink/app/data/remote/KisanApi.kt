package `in`.kisancoldlink.app.data.remote

import `in`.kisancoldlink.app.data.dto.AdvisoryDto
import `in`.kisancoldlink.app.data.dto.AdvisoryRequestDto
import `in`.kisancoldlink.app.data.dto.EnvelopeDto
import `in`.kisancoldlink.app.data.dto.IdentifyRequestDto
import `in`.kisancoldlink.app.data.dto.LiveMarketDto
import `in`.kisancoldlink.app.data.dto.LotSummaryDto
import `in`.kisancoldlink.app.data.dto.LotViewDto
import okhttp3.ResponseBody
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query
import retrofit2.http.Streaming
import retrofit2.http.Url

/** The backend's /api/v1/mobile routes (backend/app/api/mobile.py). Base URL comes from BuildConfig. */
interface KisanApi {
    @POST("mobile/identify")
    suspend fun identify(@Body body: IdentifyRequestDto): EnvelopeDto<List<LotSummaryDto>>

    @GET("mobile/lots/{lotId}")
    suspend fun lot(@Path("lotId") lotId: String, @Header(TOKEN) token: String): EnvelopeDto<LotViewDto>

    @GET("mobile/lots/{lotId}/market")
    suspend fun liveMarket(@Path("lotId") lotId: String, @Query("mandi") mandi: String, @Header(TOKEN) token: String): EnvelopeDto<LiveMarketDto>

    @POST("mobile/lots/{lotId}/advisory")
    suspend fun advisory(@Path("lotId") lotId: String, @Body body: AdvisoryRequestDto, @Header(TOKEN) token: String): EnvelopeDto<AdvisoryDto>

    /** [path] is the backend-relative audio path from the advisory, e.g. "mobile/lots/<id>/audio/<key>". */
    @Streaming
    @GET
    suspend fun audio(@Url path: String, @Header(TOKEN) token: String): ResponseBody

    companion object {
        const val TOKEN = "X-Farmer-Token"
    }
}
