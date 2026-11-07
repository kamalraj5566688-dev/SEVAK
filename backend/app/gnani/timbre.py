"""Gnani Timbre Text-to-Speech client.

Synthesizes the regional spoken summary into streaming WAV/MP3 audio and
returns it as a Base64 data URL. When the API key or endpoint is missing, or
the external call fails, returns a silent WAV fallback so the audio player
never breaks offline.
"""

from __future__ import annotations

import base64
import io
import wave
from typing import Optional

import httpx

from app.config import settings


class TimbreTTSClient:
    """Client for Gnani Timbre TTS (https://api.gnani.ai/v1/tts)."""

    def __init__(self) -> None:
        self.endpoint = settings.GNANI_TIMBRE_ENDPOINT
        self.api_key = settings.GNANI_API_KEY

    async def synthesize(
        self,
        text: str,
        language: str = "hi-IN",
        voice_gender: str = "Female",
        audio_format: str = "wav",
    ) -> dict:
        """Synthesize text to speech.

        Returns { audio_base64, audio_format, duration_seconds }.
        Falls back to a silent WAV when TTS is unavailable.
        """
        if not text:
            text = "Namaste! Main SEVAK hoon."

        if not self.api_key:
            return self._silent_audio(audio_format)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "language": language,
            "voice_gender": voice_gender,
            "audio_format": audio_format,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.endpoint, headers=headers, json=payload
                )
                response.raise_for_status()
                audio_bytes = response.content
        except Exception:
            return self._silent_audio(audio_format)

        return {
            "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
            "audio_format": audio_format,
            "duration_seconds": round(len(audio_bytes) / 16000.0, 2),
        }

    @staticmethod
    def _silent_audio(audio_format: str = "wav") -> dict:
        """Generate a ~1 second silent WAV as a graceful offline fallback."""
        sample_rate = 16000
        n_frames = sample_rate  # 1 second of silence
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(b"\x00\x00" * n_frames)
        audio_bytes = buffer.getvalue()
        return {
            "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
            "audio_format": "wav",
            "duration_seconds": 1.0,
        }


def language_to_tts_locale(language: str) -> str:
    """Map a SupportedLanguage to a Timbre TTS locale."""
    mapping = {
        "hindi": "hi-IN",
        "bhojpuri": "bho-IN",
        "maithili": "hi-IN",
        "hinglish": "hi-IN",
        "english": "en-IN",
    }
    return mapping.get(language, "hi-IN")
