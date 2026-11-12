package `in`.kisancoldlink.app.features.lot

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import `in`.kisancoldlink.app.core.networking.AppError
import `in`.kisancoldlink.app.domain.model.Advisory
import `in`.kisancoldlink.app.domain.model.AppLanguage
import `in`.kisancoldlink.app.domain.model.LivePrice
import `in`.kisancoldlink.app.domain.model.LotDetailResult
import `in`.kisancoldlink.app.domain.repository.AdvisoryRepository
import `in`.kisancoldlink.app.domain.repository.LotRepository
import `in`.kisancoldlink.app.domain.repository.SessionRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed interface LiveState {
    data object Loading : LiveState
    data class Loaded(val price: LivePrice?) : LiveState
    data class Failed(val error: AppError) : LiveState
}

data class LotUiState(
    val loading: Boolean = true,
    val language: AppLanguage = AppLanguage.TELUGU,
    val result: LotDetailResult? = null,
    val error: AppError? = null,
    val live: Map<String, LiveState> = emptyMap(),
    val lastReport: Advisory? = null,
)

/** Shared by Home, Market, My Lot and the detailed analysis. Every figure comes from the backend. */
@HiltViewModel
class LotDetailViewModel @Inject constructor(
    private val sessions: SessionRepository,
    private val lots: LotRepository,
    private val advisories: AdvisoryRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(LotUiState())
    val state: StateFlow<LotUiState> = _state.asStateFlow()

    init {
        load(force = false)
    }

    fun refresh() = load(force = true)

    private fun load(force: Boolean) {
        _state.update { it.copy(loading = true, error = null) }
        viewModelScope.launch {
            val language = sessions.language.first()
            val session = sessions.session.first()
            if (session == null) {
                _state.update { it.copy(loading = false, language = language, error = AppError.Unauthorized("no lot selected")) }
                return@launch
            }
            val report = advisories.lastReport(session, language)
            lots.lotDetail(session, force).fold(
                onSuccess = { r -> _state.update { it.copy(loading = false, language = language, result = r, error = null, lastReport = report) } },
                onFailure = { e -> _state.update { it.copy(loading = false, language = language, error = e as? AppError, lastReport = report) } },
            )
        }
    }

    fun checkLive(mandi: String) {
        if (_state.value.live[mandi] is LiveState.Loading) return
        _state.update { it.copy(live = it.live + (mandi to LiveState.Loading)) }
        viewModelScope.launch {
            val session = sessions.session.first() ?: return@launch
            val r = lots.livePrice(session, mandi).fold(
                onSuccess = { LiveState.Loaded(it) },
                onFailure = { LiveState.Failed(it as? AppError ?: AppError.Server("client_error", it.message ?: "")) },
            )
            _state.update { it.copy(live = it.live + (mandi to r)) }
        }
    }
}
