"""Server-side text-to-speech (ADR-030). Keys stay in backend/.env; the Android app only downloads MP3s.

TextToSpeechProvider is the replaceable interface; AzureSpeechProvider calls the Azure AI Speech REST API
(https://<region>.tts.speech.microsoft.com/cognitiveservices/v1) with SSML and returns MP3 bytes.
Audio is cached on disk by a hash of lot, stage, language, voice, script and TTS version.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol
from xml.sax.saxutils import escape

import httpx

from app.core.config import get_settings
from app.core.exceptions import AppError, NotConfiguredError
from app.services.advisory_script import Language

TTS_VERSION = "azure-v1"
OUTPUT_FORMAT = "audio-24khz-48kbitrate-mono-mp3"


class TtsError(AppError):
    status_code = 502
    code = "tts_failed"


class TextToSpeechProvider(Protocol):
    name: str

    def voice(self, lang: Language) -> str: ...

    def synthesize(self, text: str, lang: Language) -> bytes: ...


class AzureSpeechProvider:
    name = "azure"

    def __init__(self, key: str, region: str, voice_te: str, voice_en: str, timeout: float = 30.0) -> None:
        self.key, self.region, self.timeout = key, region, timeout
        self.voices = {"te": voice_te, "en": voice_en}

    def voice(self, lang: Language) -> str:
        return self.voices[lang]

    def synthesize(self, text: str, lang: Language) -> bytes:
        locale = "te-IN" if lang == "te" else "en-IN"
        ssml = (f"<speak version='1.0' xml:lang='{locale}'><voice name='{self.voice(lang)}'>"
                f"<prosody rate='-8%'>{escape(text)}</prosody></voice></speak>")
        try:
            r = httpx.post(
                f"https://{self.region}.tts.speech.microsoft.com/cognitiveservices/v1",
                headers={"Ocp-Apim-Subscription-Key": self.key, "Content-Type": "application/ssml+xml",
                         "X-Microsoft-OutputFormat": OUTPUT_FORMAT, "User-Agent": "kisan-cold-link"},
                content=ssml.encode("utf-8"), timeout=self.timeout,
            )
        except httpx.TimeoutException as exc:
            raise TtsError("Azure Speech timed out.") from exc
        except httpx.HTTPError as exc:
            raise TtsError(f"Azure Speech unreachable: {type(exc).__name__}.") from exc
        if r.status_code != 200 or not r.content:
            raise TtsError(f"Azure Speech returned HTTP {r.status_code}.", {"status": r.status_code})
        return r.content


def provider() -> TextToSpeechProvider:
    s = get_settings()
    if not (s.azure_speech_key.strip() and s.azure_speech_region.strip()):
        raise NotConfiguredError("Azure Speech is not configured (AZURE_SPEECH_KEY, AZURE_SPEECH_REGION).")
    return AzureSpeechProvider(s.azure_speech_key.strip(), s.azure_speech_region.strip(), s.azure_voice_te, s.azure_voice_en)


def audio_dir() -> Path:
    d = get_settings().data_dir / "advisory" / "audio"
    d.mkdir(parents=True, exist_ok=True)
    return d


def audio_key(identity: str, stage: str, lang: Language, voice: str, script: str) -> str:
    return hashlib.sha256("|".join([TTS_VERSION, identity, stage, lang, voice, script]).encode()).hexdigest()[:40]


def synthesize_cached(identity: str, stage: str, lang: Language, script: str,
                      tts: TextToSpeechProvider | None = None) -> tuple[str, str]:
    """(cache key, voice). Generates the MP3 only if this exact script/voice/version is not cached yet."""
    tts = tts or provider()
    voice = tts.voice(lang)
    key = audio_key(identity, stage, lang, voice, script)
    path = audio_dir() / f"{key}.mp3"
    if not path.exists():
        data = tts.synthesize(script, lang)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)
    return key, voice
