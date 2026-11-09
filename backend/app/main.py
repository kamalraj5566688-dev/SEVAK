"""SEVAK FastAPI application.

Creates the FastAPI app, configures CORS for the frontend dev servers, and
mounts all API routes under a single router.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes
from app.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="SEVAK - Smart Explanation & Voice-Assisted Kanoon backend",
)

# CORS: allow the Vite React frontend during local development.
# Production deployment should use the deployed frontend origin instead.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# CORS: allow the frontend dev origins (Vite on 3000/5173).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router)


@app.get("/", tags=["system"])
async def root() -> dict:
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "ok",
        "docs": "/docs",
    }
