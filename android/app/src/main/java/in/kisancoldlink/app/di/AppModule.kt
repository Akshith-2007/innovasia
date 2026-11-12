package `in`.kisancoldlink.app.di

import dagger.Binds
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import `in`.kisancoldlink.app.audio.AudioPlayer
import `in`.kisancoldlink.app.audio.ExoAudioPlayer
import `in`.kisancoldlink.app.core.preferences.SessionStore
import `in`.kisancoldlink.app.data.repository.Clock
import `in`.kisancoldlink.app.data.repository.RemoteAdvisoryRepository
import `in`.kisancoldlink.app.data.repository.RemoteFarmerRepository
import `in`.kisancoldlink.app.data.repository.RemoteLotRepository
import `in`.kisancoldlink.app.domain.repository.AdvisoryRepository
import `in`.kisancoldlink.app.domain.repository.FarmerRepository
import `in`.kisancoldlink.app.domain.repository.LotRepository
import `in`.kisancoldlink.app.domain.repository.SessionRepository
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class AppModule {
    @Binds abstract fun farmers(impl: RemoteFarmerRepository): FarmerRepository
    @Binds abstract fun lots(impl: RemoteLotRepository): LotRepository
    @Binds abstract fun advisories(impl: RemoteAdvisoryRepository): AdvisoryRepository
    @Binds abstract fun sessions(impl: SessionStore): SessionRepository
    @Binds abstract fun player(impl: ExoAudioPlayer): AudioPlayer

    companion object {
        @Provides
        @Singleton
        fun clock(): Clock = Clock { System.currentTimeMillis() }
    }
}
