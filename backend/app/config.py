"""Pydantic settings for the SEVAK backend.

All configuration is sourced from environment variables (.env supported).
Every value is optional: when Gnani/Hugging Face credentials are missing the
backend gracefully degrades to a realistic Indic legal demo fallback instead
of crashing.
"""

import json
from pathlib import Path
from typing import Any, List, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "SEVAK Backend"
    APP_VERSION: str = "1.0.0"

    # Gnani AI credentials
    GNANI_API_KEY: str = ""
    GNANI_PRISMA_ENDPOINT: str = "https://api.vachana.ai/stt/v3"
    GNANI_TIMBRE_ENDPOINT: str = "https://api.gnani.ai/v1/tts"

    # Hugging Face Dedicated Inference Endpoint or Serverless Model ID (Evon 30B)
    HF_TOKEN: str = ""
    HF_EVON_ENDPOINT: str = ""
    HF_MODEL_ID: str = ""

    # CORS (can be JSON array or comma-separated string in .env)
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://localhost:5173"]

    # Upload limits
    MAX_FILE_SIZE_MB: int = 10

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def normalize_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                try:
                    parsed = json.loads(v_stripped)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    pass
            return [origin.strip() for origin in v_stripped.split(",") if origin.strip()]
        if isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]
        return ["http://localhost:3000", "http://localhost:5173"]

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


def is_gnani_configured() -> bool:
    """Return True when a Gnani API key is present."""
    return bool(settings.GNANI_API_KEY)


def is_evon_configured() -> bool:
    """Return True when Hugging Face Evon credentials (token and endpoint or model ID) are present."""
    return bool(settings.HF_TOKEN and (settings.HF_EVON_ENDPOINT or settings.HF_MODEL_ID))


