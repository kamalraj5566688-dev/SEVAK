"""SEVAK API routes.

Endpoints (all match the frontend client in src/services/api.ts):

  GET    /health
  POST   /api/analyze-document   (multipart: document + language)
  POST   /api/voice/transcribe   (multipart: audio + language) -> { transcript }
  POST   /api/ask                (JSON: question, documentId?, language) -> { answer }
  POST   /api/voice-query        (alias for /api/ask)
  POST   /api/tts                (JSON: text, language) -> { audio_base64, ... }

All uploads are ephemeral: bytes are processed in-memory and released after the
request. No database or persistent storage is used.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.config import settings
from app.gnani.evon import EvonReasoningClient
from app.gnani.prisma import PrismaSTTClient, clean_indic_transcript
from app.gnani.timbre import TimbreTTSClient, language_to_tts_locale
from app.ingestion.ocr import ocr_image_chunks
from app.ingestion.pdf_parser import compose_document_text as pdf_compose
from app.ingestion.pdf_parser import extract_pdf_chunks
from app.ingestion.ocr import compose_document_text as ocr_compose
from app.schemas import (
    Category,
    DeadlineBlock,
    EvonAnalysisResult,
    NextStepItem,
    RightsBlock,
    SevakApiResponse,
    SourceBlock,
    UrgencyLevel,
    WhatBlock,
    WhyBlock,
)
router = APIRouter()

evon = EvonReasoningClient()
prisma = PrismaSTTClient()
timbre = TimbreTTSClient()

# Allowed upload extensions / MIME types.
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
}

MAX_FILE_SIZE = settings.MAX_FILE_SIZE_MB * 1024 * 1024

# Statutory safety-shield disclaimer injected into every analysis.
SAFETY_DISCLAIMER = (
    "SEVAK is an AI document-assistant, not a lawyer. It explains clauses in "
    "simple language and does not make binding legal predictions or guarantee "
    "legal outcomes. For any legal dispute, consult a qualified advocate or "
    "legal-aid clinic."
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def _format_size(size_bytes: int) -> str:
    mb = size_bytes / (1024 * 1024)
    if mb >= 1:
        return f"{mb:.1f} MB"
    kb = size_bytes / 1024
    return f"{kb:.0f} KB" if kb >= 1 else f"{size_bytes} bytes"


def _detect_category(text: str) -> tuple[Category, float]:
    """Detect category from grounded OCR text with a confidence score.

    Keyword matching runs against the actual extracted document text (not the
    model's free-text prose), so classification is grounded in evidence.
    Specific keywords are checked before generic ones to resolve overlaps.
    Returns (category, confidence) where confidence is 1.0 on a keyword match
    and 0.5 for the Government Notice default.
    """
    lowered = text.lower()
    if any(k in lowered for k in ["challan", "over-speeding", "overspeeding", "red-light", "traffic police", "motor vehicle", "rc ", "registration certificate"]):
        return "Traffic Police Notice", 1.0
    if any(k in lowered for k in ["re-kyc", "kyc", "sbi", "hdfc", "upi", "aadhaar", "pan", "bank account"]):
        return "Banking & KYC", 1.0
    if any(k in lowered for k in ["income tax", "itd", "assessment", "nefac", "142(", "taxpayer"]):
        return "Income Tax Department", 1.0
    if any(k in lowered for k in ["court", "summons", "section 138", "ni act", "negotiable instruments", "legal notice"]):
        return "Legal Summons", 1.0
    return "Government Notice", 0.5


def _split_title_description(text: str) -> tuple[str, str]:
    """Split a next-step sentence into (title, description)."""
    text = text.strip()
    match = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)
    if len(match) == 2:
        return match[0].strip(), match[1].strip()
    return text, ""


def _map_evon_to_response(
    *,
    evon: EvonAnalysisResult,
    filename: str,
    file_size_bytes: int,
    file_type: str,
    language: str,
    chunks_confidence: float,
    classification_confidence: float,
    category: Category,
    audio_base64: Optional[str],
    demo_fallback: bool,
) -> SevakApiResponse:
    """Map the raw Evon result into the frontend-compatible SevakApiResponse."""
    doc_text_source = ""

    # Issuing authority / legal section / reference extracted from 'what' text.
    issuing_authority = "Competent Authority"
    legal_section = "Not specified in document"
    reference_number = f"SEVAK-{uuid.uuid4().hex[:8].upper()}"

    m_auth = re.search(r"(?:issued by|issuing authority|authority)[:\-]\s*([^.\n]+)", evon.what, re.IGNORECASE)
    if m_auth:
        issuing_authority = m_auth.group(1).strip()
    m_section = re.search(r"(?:section|under|sec\.?)\s*([0-9A-Za-z\(\)\-\/]+)", evon.why + " " + evon.what, re.IGNORECASE)
    if m_section:
        legal_section = m_section.group(1).strip()

    # Deadlines block.
    deadline_items = evon.deadlines or []
    has_deadline = len(deadline_items) > 0
    deadline_date = None
    days_remaining: Optional[int] = None
    consequence_text = None
    if deadline_items:
        first = deadline_items[0]
        deadline_date = first.timeline
        m_days = re.search(r"(\d+)\s*(day|din|days)", first.timeline, re.IGNORECASE)
        if m_days:
            days_remaining = int(m_days.group(1))
        consequence_text = f"Action '{first.action}' is due {first.timeline} per {first.source_page}."

    urgency_map = {"GREEN": "low", "YELLOW": "medium", "RED": "high"}
    urgency_level: UrgencyLevel = urgency_map[evon.severity]

    # Next steps: exactly 3.
    next_steps: list[NextStepItem] = []
    for idx, step_text in enumerate(evon.next_steps[:3], start=1):
        title, description = _split_title_description(step_text)
        next_steps.append(
            NextStepItem(
                step=idx,
                title=title or f"Action {idx}",
                description=description or step_text,
            )
        )

    # Rights safeguards: split rights_and_protections into sentences.
    raw_safeguards = [s.strip() for s in re.split(r"(?<=[.!?])\s+", evon.rights_and_protections) if s.strip()]
    safeguards = raw_safeguards[:5] if raw_safeguards else ["Seek clarification from the issuing authority before acting."]

    # Voice summaries: one regional summary echoed across supported languages.
    spoken = evon.spoken_summary_regional or "Namaste! Main SEVAK hoon. Aapka notice aaya hai, kripya ise padhkar time par action lein."
    voice_summaries = {
        "hinglish": spoken,
        "hindi": spoken,
        "english": spoken,
        "bhojpuri": spoken,
        "maithili": spoken,
    }

    # Document title from 'what' (first clause) or generic.
    document_title = evon.what.split(".")[0].strip() if evon.what else "Official Notice"
    if len(document_title) > 80:
        document_title = document_title[:80].rstrip() + "..."

    return SevakApiResponse(
        id=str(uuid.uuid4()),
        document_title=document_title,
        category=category,
        original_file_name=filename,
        file_size=_format_size(file_size_bytes),
        file_type=file_type,
        upload_date=_now_iso(),
        confidence_score=round(classification_confidence, 2),
        classification_confidence=round(classification_confidence, 2),
        is_demo_fallback=demo_fallback,
        what=WhatBlock(summary=evon.what, details=evon.why),
        why=WhyBlock(significance=evon.why, urgency_reason=evon.severity_reason),
        next_steps=next_steps,
        rights=RightsBlock(
            title="Aapke Adhikar (Citizen Protections)",
            safeguards=safeguards,
            disclaimer=SAFETY_DISCLAIMER,
        ),
        deadline=DeadlineBlock(
            has_deadline=has_deadline,
            date=deadline_date,
            days_remaining=days_remaining,
            urgency_level=urgency_level,
            consequence_text=consequence_text,
        ),
        source=SourceBlock(
            issuing_authority=issuing_authority,
            legal_section=legal_section,
            reference_number=reference_number,
            official_portal_url=None,
        ),
        voice_summaries=voice_summaries,
        audio_base64=audio_base64,
        citations=evon.citations or [],
    )


@router.get("/health", tags=["system"])
async def health() -> dict:
    return {
        "status": "ok",
        "service": "SEVAK Backend",
        "version": settings.APP_VERSION,
    }


@router.post("/api/analyze-document", tags=["analysis"])
async def analyze_document(
    document: UploadFile = File(...),
    language: str = Form("hinglish"),
) -> SevakApiResponse:
    """Analyze an uploaded PDF or image document end-to-end."""
    # ---- Validate file type & size -------------------------------------
    filename = document.filename or "uploaded_document"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if f".{ext}" not in ALLOWED_EXTENSIONS or (document.content_type or "") not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type. Please upload a PDF, PNG, JPG, or WEBP document.",
        )

    content = await document.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds the {settings.MAX_FILE_SIZE_MB} MB limit.",
        )
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # ---- Extract text chunks (ephemeral, in-memory) --------------------
    is_pdf = ext == "pdf" or (document.content_type or "") == "application/pdf"
    demo_fallback = False
    try:
        if is_pdf:
            chunks = extract_pdf_chunks(content, filename)
            document_text = pdf_compose(chunks)
        else:
            chunks, ocr_fallback = ocr_image_chunks(content, filename)
            document_text = ocr_compose(chunks)
            demo_fallback = ocr_fallback
    except HTTPException:
        raise
    except Exception as exc:
        # Last-resort: degrade to demo analysis rather than crashing.
        demo_fallback = True
        document_text = ""
        chunks = []

    # ---- Average chunk confidence --------------------------------------
    avg_confidence = (
        sum(c.confidence_score for c in chunks) / len(chunks) if chunks else 0.5
    )

    # ---- Category detection (grounded in OCR text, gated on fallback) ----
    if demo_fallback and not document_text.strip():
        # No real document text was extracted: do not fabricate a category.
        category: Category = "Unrecognized / Not a Document"
        classification_confidence = 0.0
    else:
        category, classification_confidence = _detect_category(document_text)

    # ---- Evon 30B reasoning --------------------------------------------
    try:
        evon_result = await evon.analyze(document_text, language=language)
    except Exception:
        demo_fallback = True
        evon_result = EvonAnalysisResult(
            severity="YELLOW",
            severity_reason="Reasoning engine unavailable in fallback mode.",
            what="Official document notice requiring attention.",
            why="An authority has issued a notice that needs your response.",
            next_steps=[
                "Read the notice carefully.",
                "Note the issuing authority and reference number.",
                "Act before the stated deadline.",
            ],
            rights_and_protections="Seek clarification from the issuing authority or a qualified lawyer if unsure.",
            deadlines=[],
            citations=[],
            spoken_summary_regional="Namaste! Main SEVAK hoon. Aapka notice aaya hai, kripya ise padhkar time par action lein.",
        )

    # ---- Timbre TTS for the spoken summary -----------------------------
    audio_base64: Optional[str] = None
    try:
        tts_result = await timbre.synthesize(
            text=evon_result.spoken_summary_regional,
            language=language,
        )
        audio_base64 = tts_result.get("audio_base64")
    except Exception:
        audio_base64 = None

    response = _map_evon_to_response(
        evon=evon_result,
        filename=filename,
        file_size_bytes=len(content),
        file_type=document.content_type or "application/octet-stream",
        language=language,
        chunks_confidence=avg_confidence,
        classification_confidence=classification_confidence,
        category=category,
        audio_base64=audio_base64,
        demo_fallback=demo_fallback,
    )
    return response


@router.post("/api/voice/transcribe", tags=["voice"])
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form("auto"),
) -> dict:
    """Transcribe an audio blob via Gnani Prisma STT."""
    content = await audio.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio blob is empty.",
        )

    result = await prisma.transcribe(
        audio_bytes=content,
        filename=audio.filename or "audio.wav",
        language=language,
    )
    transcript = clean_indic_transcript(result.get("transcription", ""))
    return {
        "transcript": transcript,
        "detected_language": result.get("detected_language", language),
        "confidence": result.get("confidence", 0.0),
        "status": result.get("status", "SUCCESS"),
    }


async def _answer_from_evon(question: str, language: str) -> str:
    """Answer a follow-up question using Evon 30B or fallback."""
    return await evon.ask(question=question, language=language)


def _demo_answer(question: str, language: str) -> str:
    return EvonReasoningClient._demo_answer(question, language)


@router.post("/api/ask", tags=["voice"])
async def ask_question(payload: dict) -> dict:
    """Answer a follow-up voice/text question about a document."""
    question = payload.get("question", "")
    document_id = payload.get("documentId")
    language = payload.get("language", "hinglish")

    if not question or not str(question).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question is required.",
        )

    try:
        answer = await _answer_from_evon(str(question), str(language))
    except Exception:
        answer = _demo_answer(str(question), str(language))

    return {"answer": answer, "documentId": document_id, "response": answer}


@router.post("/api/voice-query", tags=["voice"])
async def voice_query(payload: dict) -> dict:
    """Alias for /api/ask (matches the task-spec endpoint name)."""
    return await ask_question(payload)


@router.post("/api/tts", tags=["voice"])
async def synthesize_tts(payload: dict) -> dict:
    """Synthesize text into speech audio via Gnani Timbre."""
    text = payload.get("text", "")
    language = payload.get("language", "hi-IN")
    voice_gender = payload.get("voice_gender", "Female")
    audio_format = payload.get("audio_format", "wav")

    if not text or not str(text).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text is required.",
        )

    result = await timbre.synthesize(
        text=str(text),
        language=language_to_tts_locale(str(language)),
        voice_gender=str(voice_gender),
        audio_format=str(audio_format),
    )
    return {
        "audio_base64": result["audio_base64"],
        "audio_format": result["audio_format"],
        "duration_seconds": result["duration_seconds"],
    }
