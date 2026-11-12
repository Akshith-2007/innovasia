package `in`.kisancoldlink.app.navigation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import `in`.kisancoldlink.app.domain.model.AppLanguage
import `in`.kisancoldlink.app.domain.repository.SessionRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

/** Decides the first screen once DataStore has been read (null until then). */
@HiltViewModel
class RootViewModel @Inject constructor(sessions: SessionRepository) : ViewModel() {
    val language: StateFlow<AppLanguage> = sessions.language.stateIn(viewModelScope, SharingStarted.Eagerly, AppLanguage.TELUGU)
    private val _start = MutableStateFlow<String?>(null)
    val startRoute: StateFlow<String?> = _start.asStateFlow()

    init {
        viewModelScope.launch {
            _start.value = when {
                !sessions.onboarded.first() -> Routes.WELCOME
                sessions.session.first() == null -> Routes.AUTH
                else -> Routes.HOME
            }
        }
    }
}
