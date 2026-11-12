package `in`.kisancoldlink.app.core.networking

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import retrofit2.HttpException
import java.io.IOException

/** Every failure the UI can show. Nothing is replaced with made-up values. */
sealed class AppError(message: String) : Exception(message) {
    /** Backend unreachable, timeout, DNS, no internet. */
    class Network(message: String) : AppError(message)
    /** Name + number match no admin-created lot. */
    class NotRegistered(message: String) : AppError(message)
    /** Token rejected: the lot was removed or its number changed. */
    class Unauthorized(message: String) : AppError(message)
    /** Backend replied with an error envelope (code + message). */
    class Server(val code: String, message: String) : AppError(message)
}

@Serializable
private data class ErrorBody(val code: String = "http_error", val message: String = "")

@Serializable
private data class ErrorEnvelope(val error: ErrorBody? = null)

private val errorJson = Json { ignoreUnknownKeys = true }

fun Throwable.toAppError(): AppError = when (this) {
    is AppError -> this
    is HttpException -> {
        val body = runCatching { response()?.errorBody()?.string() }.getOrNull()
        val err = body?.let { runCatching { errorJson.decodeFromString<ErrorEnvelope>(it).error }.getOrNull() }
        when (err?.code) {
            "farmer_not_registered" -> AppError.NotRegistered(err.message)
            "unauthorized" -> AppError.Unauthorized(err.message)
            null -> AppError.Server("http_${code()}", "HTTP ${code()}")
            else -> AppError.Server(err.code, err.message)
        }
    }
    is IOException -> AppError.Network(message ?: "network error")
    else -> AppError.Server("client_error", message ?: javaClass.simpleName)
}

suspend fun <T> apiCall(block: suspend () -> T): Result<T> =
    try {
        Result.success(block())
    } catch (e: kotlinx.coroutines.CancellationException) {
        throw e
    } catch (e: Throwable) {
        Result.failure(e.toAppError())
    }
