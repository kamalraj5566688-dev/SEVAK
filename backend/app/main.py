"""SEVAK FastAPI application.

Creates the FastAPI app, configures CORS for the frontend dev servers, and
mounts all API routes under a single router.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.api import routes
from app.config import settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="SEVAK - Smart Explanation & Voice-Assisted Kanoon backend",
)

# CORS: allow the Vite React frontend during local development.
# Production deployment should use the deployed frontend origin instead.
# NOTE: allow_credentials=True is incompatible with allow_origins=["*"].
# Wildcard origins are rejected when credentials are enabled.
_cors_origins = list(
    set(
        ["http://localhost:3000", "http://127.0.0.1:3000"]
        + (
            settings.CORS_ORIGINS
            if isinstance(settings.CORS_ORIGINS, list)
            else [settings.CORS_ORIGINS]
        )
    )
)
if "*" in _cors_origins:
    _cors_origins.remove("*")
    logger.warning("Wildcard CORS origin removed (incompatible with allow_credentials=True).")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
)


# Security headers middleware (M-02 CSP, M-03 HSTS, L-01 X-Frame-Options)
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response: Response = await call_next(request)

    # Content-Security-Policy (M-02)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://plausible.io https://browser.sentry-cdn.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://api.vachana.ai https://plausible.io https://browser.sentry-cdn.com; "
        "media-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self';"
    )

    # HTTP Strict Transport Security (M-03)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    # X-Frame-Options: DENY to prevent clickjacking (L-01)
    response.headers["X-Frame-Options"] = "DENY"

    # X-Content-Type-Options: prevent MIME sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Referrer-Policy: limit referrer information
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Permissions-Policy: restrict powerful features
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), "
        "payment=(), usb=(), magnetometer=(), gyroscope=()"
    )

    return response


app.include_router(routes.router)


@app.get("/", tags=["system"])
async def root() -> dict:
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "ok",
        "docs": "/docs",
    }
