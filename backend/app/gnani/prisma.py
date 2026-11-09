"""Gnani Prisma v3 Speech-to-Text client.

Uses the verified Prisma v3 multipart REST contract:
- Endpoint: https://api.vachana.ai/stt/v3
- Header: X-API-Key-ID
- File field: audio_file
- Form fields: language_code, preferred_language, format,
  itn_native_numerals

Falls back to a deterministic demo transcript when the API key is missing
or the external service is unavailable, so the voice flow remains usable
offline.
"""

from __future__ import annotations

import re
from typing import Optional

import httpx

from app.config import settings


class PrismaSTTClient:
    """Client for Gnani Prisma v3 STT."""

    def __init__(self) -> None:
        self.endpoint = settings.GNANI_PRISMA_ENDPOINT
        self.api_key = settings.GNANI_API_KEY

    async def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "audio.wav",
        language: Optional[str] = None,
    ) -> dict:
        """Transcribe audio bytes using Prisma v3.

        Returns a normalized dict:
        {
            status,
            transcription,
            detected_language,
            confidence
        }
        """
        lang = self._normalize_language(language)

        # No API key -> deterministic offline fallback.
        if not self.api_key:
            return self._demo_transcript(lang)

        headers = {
            "X-API-Key-ID": self.api_key,
        }

        data = {
            "language_code": lang,
            "preferred_language": lang,
            "format": "transcribe",
            "itn_native_numerals": "true",
        }

        files = {
            "audio_file": (
                filename,
                audio_bytes,
                "audio/wav",
            )
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.endpoint,
                    headers=headers,
                    files=files,
                    data=data,
                )

                response.raise_for_status()
                payload = response.json()

        except httpx.HTTPStatusError as exc:
            return {
                "status": "ERROR",
                "transcription": "",
                "detected_language": lang,
                "confidence": 0.0,
                "error": f"Prisma HTTP {exc.response.status_code}",
            }

        except httpx.RequestError as exc:
            return {
                "status": "ERROR",
                "transcription": "",
                "detected_language": lang,
                "confidence": 0.0,
                "error": f"Prisma request error: {type(exc).__name__}",
            }

        except Exception as exc:
            return {
                "status": "ERROR",
                "transcription": "",
                "detected_language": lang,
                "confidence": 0.0,
                "error": f"Prisma unexpected error: {type(exc).__name__}",
            }

        # Prisma v3 verified response field:
        # payload["transcript"]
        transcript = (
            payload.get("transcript")
            or payload.get("transcription")
            or payload.get("output", {}).get("literal")
            or ""
        )

        detected_language = (
            payload.get("detected_language")
            or lang
        )

        # Prisma does not necessarily return a confidence value.
        confidence = payload.get("confidence")

        if confidence is None:
            confidence = 0.95 if transcript else 0.0

        return {
            "status": "SUCCESS" if payload.get("success", True) else "ERROR",
            "transcription": clean_indic_transcript(transcript),
            "detected_language": detected_language,
            "confidence": float(confidence),
        }

    @staticmethod
    def _normalize_language(language: Optional[str]) -> str:
        """Map SEVAK language names to Prisma-supported language codes."""
        value = (language or "").strip().lower()

        mapping = {
            "hindi": "hi-IN",
            "hi": "hi-IN",
            "hi-in": "hi-IN",

            "english": "en-IN",
            "en": "en-IN",
            "en-in": "en-IN",

            "hinglish": "indic-auto",
            "indic-auto": "indic-auto",
            "auto": "indic-auto",

            # Prisma does not expose dedicated Bhojpuri/Maithili
            # codes in the supported-language list, so use Indic
            # automatic language detection.
            "bhojpuri": "indic-auto",
            "maithili": "indic-auto",
        }

        return mapping.get(value, "indic-auto")

    @staticmethod
    def _demo_transcript(language: str) -> dict:
        """Safe fallback when live Prisma STT is unavailable."""
        return {
            "status": "ERROR",
            "transcription": "",
            "detected_language": language,
            "confidence": 0.0,
            "error": "Live Prisma STT unavailable",
        }


def clean_indic_transcript(text: str) -> str:
    """Light cleanup for Indic dialect / code-mixed transcripts."""
    if not text:
        return ""

    text = text.strip()

    # Collapse repeated whitespace.
    text = re.sub(r"\s+", " ", text)

    # Remove repeated punctuation.
    text = re.sub(r"([.,!?])\1+", r"\1", text)

    return text




