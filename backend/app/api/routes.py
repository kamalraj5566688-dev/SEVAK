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
from app.ai.grounding import (
    build_grounded_context,
    extract_calendar_date,
    extract_relative_days,
    validate_citations,
)
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

# Short-lived in-memory document context for follow-up questions.
# Documents are not persisted to a database.
DOCUMENT_CONTEXT_STORE: dict[str, dict] = {}
MAX_DOCUMENT_CONTEXTS = 20

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
    document_id: str,
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

        try:
            parsed_deadline = datetime.fromisoformat(str(first.timeline))
            days_remaining = (
                parsed_deadline.date() - datetime.now().date()
            ).days
        except (TypeError, ValueError):
            m_days = re.search(
                r"(\d+)\s*(day|din|days)",
                str(first.timeline),
                re.IGNORECASE,
            )
            if m_days:
                days_remaining = int(m_days.group(1))

        consequence_text = (
            f"Action '{first.action}' is due by {first.timeline}."
        )

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
        id=document_id,
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


def _local_document_analysis(
    document_text: str,
    language: str,
) -> EvonAnalysisResult:
    """Grounded local fallback used when Evon is unavailable.

    This fallback uses only information explicitly extracted from the
    uploaded document. It does not invent legal conclusions.
    """
    import re
    from datetime import datetime, timedelta

    text = re.sub(r"\s+", " ", (document_text or "")).strip()

    if not text:
        return EvonAnalysisResult(
            severity="YELLOW",
            severity_reason="No readable document text was extracted.",
            what="SEVAK could not extract readable text from this document.",
            why=(
                "A document-specific analysis cannot be safely produced "
                "without readable evidence."
            ),
            next_steps=[
                "Try uploading a clearer PDF or image.",
                "Check that the document contains readable text.",
                "If necessary, provide the document text manually.",
            ],
            rights_and_protections=(
                "Do not rely on an unverified interpretation when the "
                "document text is unavailable."
            ),
            deadlines=[],
            citations=[],
            spoken_summary_regional=(
                "Namaste! Document ka readable text available nahi hai, "
                "isliye main safe analysis nahi kar sakta."
            ),
        )

    def first_match(patterns):
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    subject = first_match([
        r"Subject\s*:\s*(.+?)(?=\s+Date\s*:|\s+Dear\s+Customer\b|$)",
        r"विषय\s*:\s*(.+?)(?=\s+दिनांक|$)",
    ])

    amount = first_match([
        r"(?:Rs\.?|INR|₹)\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
        r"amount\s+(?:of|is)\s+(?:Rs\.?|INR|₹)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
    ])

    deadline = first_match([
        r"\bwithin\s+(\d+\s+(?:days?|weeks?|months?))\b",
        r"\bwithin\s+(\d+)\s+(days?|weeks?|months?)\b",
    ])

    date_value = first_match([
        r"\bDate\s*:\s*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})",
        r"\bDate\s*:\s*([A-Za-z]+\s+[0-9]{1,2},?\s+[0-9]{4})",
        r"\bDate\s*:\s*([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})",
    ])

    reference = first_match([
        r"(?:Reference|Ref\.?|Reference\s+Number)"
        r"\s*(?:No\.?|Number)?\s*:\s*([A-Za-z0-9./_-]+)",
    ])

    deadline_date = None

    if deadline and date_value:
        deadline_match = re.search(
            r"(\d+)\s+(days?|weeks?|months?)",
            deadline,
            re.IGNORECASE,
        )

        if deadline_match:
            count = int(deadline_match.group(1))
            unit = deadline_match.group(2).lower()

            parsed_date = None

            for fmt in (
                "%d %B %Y",
                "%d %b %Y",
                "%B %d %Y",
                "%b %d %Y",
                "%d/%m/%Y",
                "%d-%m-%Y",
                "%d/%m/%y",
                "%d-%m-%y",
            ):
                try:
                    parsed_date = datetime.strptime(
                        date_value.replace(",", ""),
                        fmt,
                    )
                    break
                except ValueError:
                    continue

            if parsed_date:
                if unit.startswith("day"):
                    deadline_date = parsed_date + timedelta(days=count)
                elif unit.startswith("week"):
                    deadline_date = parsed_date + timedelta(weeks=count)
                elif unit.startswith("month"):
                    deadline_date = parsed_date + timedelta(days=count * 30)

    facts = []

    if subject:
        facts.append(f"Subject: {subject}")

    if date_value:
        facts.append(f"Date: {date_value}")

    if amount:
        facts.append(f"Amount mentioned: Rs. {amount}")

    if deadline:
        facts.append(f"Response/payment period mentioned: {deadline}")

    if deadline_date:
        facts.append(
            f"Calculated deadline from the document date: "
            f"{deadline_date.strftime('%d %B %Y')}"
        )

    if reference:
        facts.append(f"Reference number: {reference}")

    if subject:
        what = f"The document contains a notice concerning: {subject}."
    elif facts:
        what = "The document contains the following extracted facts: " + "; ".join(facts)
    else:
        what = (
            "The document contains readable text, but no specific structured "
            "facts were confidently extracted."
        )

    if amount and deadline:
        why = (
            f"The document explicitly mentions an amount of Rs. {amount} "
            f"and a payment/response period of {deadline}."
        )
    elif deadline:
        why = (
            f"The document explicitly states a time period of {deadline}, "
            "which should be noted."
        )
    elif amount:
        why = (
            f"The document explicitly mentions an amount of Rs. {amount}. "
            "The original document should be checked before taking action."
        )
    else:
        why = (
            "The document-specific information should be reviewed against "
            "the actual wording before taking action."
        )

    if deadline:
        severity_reason = (
            "The document contains an explicit time-related requirement."
        )

        if deadline_date:
            first_step = (
                f"Note the stated {deadline} period; the calculated date "
                f"from the document date is {deadline_date.strftime('%d %B %Y')}."
            )
        else:
            first_step = (
                f"Note the stated {deadline} time period and keep the "
                "document safely stored."
            )
    else:
        severity_reason = (
            "The document requires attention, but no explicit deadline "
            "was extracted."
        )
        first_step = (
            "Read the complete notice and identify any response or payment requirement."
        )

    second_step = (
        f"Verify the amount mentioned in the document: Rs. {amount}."
        if amount
        else
        "Verify the important facts directly against the original document."
    )

    next_steps = [
        first_step,
        second_step,
        "Use the issuing authority's official contact channel if clarification is required.",
    ]

    spoken = ["Namaste! Main SEVAK hoon."]

    if subject:
        spoken.append(f"Document mein {subject} diya gaya hai.")
    else:
        spoken.append("Document se kuch important information mili hai.")

    if amount:
        spoken.append(f"Outstanding amount Rs. {amount} hai.")

    if deadline:
        if deadline_date:
            spoken.append(
                f"Payment ya response ke liye {deadline} ka period diya gaya hai. "
                f"Document ki date ke basis par calculated date "
                f"{deadline_date.strftime('%d %B %Y')} hai."
            )
        else:
            spoken.append(
                f"Document mein {deadline} ka time period diya gaya hai."
            )

    if reference:
        spoken.append(f"Reference number {reference} hai.")

    deadline_records = []

    if deadline:
        deadline_records.append({
            "text": deadline,
            "date": deadline_date.strftime("%Y-%m-%d") if deadline_date else None,
            "days_remaining": None,
            "urgency_level": "medium",
            "consequence": None,
            "action": "Complete the required action stated in the notice.",
            "timeline": deadline_date.strftime("%Y-%m-%d") if deadline_date else deadline,
            "source_page": 1,
        })

    return EvonAnalysisResult(
        severity="YELLOW",
        severity_reason=severity_reason,
        what=what,
        why=why,
        next_steps=next_steps,
        rights_and_protections=(
            "SEVAK is showing information explicitly extracted from "
            "the document. For legal or financial decisions, verify "
            "the original notice and consult the appropriate official "
            "authority or qualified professional when necessary."
        ),
        deadlines=deadline_records,
        citations=[],
        spoken_summary_regional=" ".join(spoken),
    )
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
    # ---- Evon 30B reasoning --------------------------------------------
    try:
        evon_result = await evon.analyze(document_text, language=language)
    except Exception:
        demo_fallback = True
        evon_result = _local_document_analysis(
            document_text=document_text,
            language=language,
        )

    # Evon may return a generic fallback result instead of raising an
    # exception when the reasoning service is unavailable. Detect that
    # response and switch to the document-grounded local analysis.
    evon_unavailable = (
        "reasoning service is currently unavailable" in str(evon_result.what).lower()
        or "reasoning engine unavailable" in str(evon_result.severity_reason).lower()
        or "could not complete a grounded analysis" in str(evon_result.what).lower()
    )

    if evon_unavailable:
        demo_fallback = True
        evon_result = _local_document_analysis(
            document_text=document_text,
            language=language,
        )

    # ---- Validate Evon citations against real extracted evidence --------
    evon_result.citations = validate_citations(
        evon_result.citations,
        chunks,
    )

    # ---- Create stable document ID for this analysis --------------------
    document_id = str(uuid.uuid4())

    # ---- Build grounded context for follow-up questions -----------------
    grounded_context = build_grounded_context(chunks)

    if grounded_context:
        DOCUMENT_CONTEXT_STORE[document_id] = {
            "grounded_context": grounded_context,
            "created_at": _now_iso(),
            "filename": filename,
        }

        # Keep memory bounded on this lightweight deployment.
        while len(DOCUMENT_CONTEXT_STORE) > MAX_DOCUMENT_CONTEXTS:
            oldest_id = next(iter(DOCUMENT_CONTEXT_STORE))
            DOCUMENT_CONTEXT_STORE.pop(oldest_id, None)
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
        document_id=document_id,
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


def _clean_grounded_text(text: str) -> str:
    """Normalize extracted document text without changing its facts."""
    if not text:
        return ""

    value = str(text)

    # Convert escaped newline representations into real line breaks.
    value = value.replace("\\r\\n", "\n")
    value = value.replace("\\n", "\n")

    # Some earlier extraction paths produced literal 'n n'.
    value = re.sub(r"(?i)\bn\s+n\b", "\n", value)

    # Normalize whitespace while preserving paragraph boundaries.
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n[ \t]+", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)

    return value.strip()


def _extract_grounded_evidence(context: str) -> list[dict]:
    """Extract [Page X, Paragraph Y] evidence blocks."""
    if not context:
        return []

    cleaned = _clean_grounded_text(context)

    pattern = (
        r"\[(Page\s+\d+,\s*Paragraph\s+\d+)\]"
        r"\s*(.*?)(?=\[Page\s+\d+,\s*Paragraph\s+\d+\]|\Z)"
    )

    matches = re.findall(pattern, cleaned, flags=re.IGNORECASE | re.DOTALL)

    evidence = []

    for location, text in matches:
        text = _clean_grounded_text(text)

        if text:
            evidence.append(
                {
                    "location": location,
                    "text": text,
                }
            )

    # If the context has no explicit evidence markers, keep it usable
    # instead of inventing a citation.
    if not evidence and cleaned:
        evidence.append(
            {
                "location": None,
                "text": cleaned,
            }
        )

    return evidence


def _question_terms(question: str) -> set[str]:
    """Extract meaningful English/Hindi/Hinglish question terms."""
    stopwords = {
        "what", "is", "are", "the", "this", "that", "document",
        "mein", "me", "kya", "hai", "hain", "ka", "ke", "ki",
        "ko", "ye", "yeh", "woh", "wo", "mujhe", "batao", "bataye",
        "sirf", "document", "basis", "par", "do", "dena", "please",
        "how", "when", "where", "which", "does", "did", "can",
        "give", "tell", "about", "from", "according", "to",
    }

    words = re.findall(r"[a-zA-Z0-9\u0900-\u097F]+", question.lower())

    return {
        word
        for word in words
        if len(word) > 2 and word not in stopwords
    }


def _score_evidence(question: str, text: str) -> int:
    """Score evidence by meaningful question-term overlap."""
    terms = _question_terms(question)
    lowered = text.lower()

    score = 0

    for term in terms:
        if term in lowered:
            score += 1

    # Give extra weight to common high-value document fields.
    q = question.lower()

    if any(k in q for k in ["amount", "paise", "rupaye", "₹", "rs"]):
        if re.search(r"(?:₹|rs\.?|inr)\s*[\d,]+", lowered, re.IGNORECASE):
            score += 5

    if any(k in q for k in ["deadline", "kab tak", "last date", "days", "tarikh", "date"]):
        if re.search(r"\b(?:within|in)\s+\d+\s+days?\b", lowered, re.IGNORECASE):
            score += 5

        if re.search(
            r"\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)",
            lowered,
            re.IGNORECASE,
        ):
            score += 3

    if any(k in q for k in ["subject", "notice", "kis baare", "kya notice"]):
        if "subject" in lowered or "notice" in lowered:
            score += 4

    return score


def _extract_key_facts(text: str) -> list[str]:
    """Extract only facts explicitly present in the selected evidence."""
    facts = []

    # Currency / amount.
    amount_matches = re.findall(
        r"(?:₹|Rs\.?|INR)\s*[\d,]+(?:\.\d+)?",
        text,
        flags=re.IGNORECASE,
    )

    for amount in amount_matches:
        if amount not in facts:
            facts.append(amount)

    # Deadline phrasing.
    deadline_matches = re.findall(
        r"(?:within|in)\s+\d+\s+days?(?:\s+from\s+[^.]+)?",
        text,
        flags=re.IGNORECASE,
    )

    for deadline in deadline_matches:
        cleaned = deadline.strip()
        if cleaned not in facts:
            facts.append(cleaned)

    # Explicit dates.
    date_matches = re.findall(
        r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|"
        r"August|September|October|November|December)\s+\d{4}\b",
        text,
        flags=re.IGNORECASE,
    )

    for date in date_matches:
        if date not in facts:
            facts.append(date)

    return facts


def _local_grounded_answer(
    question: str,
    language: str,
    context: str | None = None,
) -> str:
    """Produce a document-grounded answer when Evon is unavailable."""

    if not context:
        q = (question or "").strip().lower()

        greeting_markers = (
            "hello", "hi", "hey", "namaste", "namaskar",
            "hii", "helo", "good morning", "good afternoon",
            "good evening",
        )

        how_are_you_markers = (
            "how are you", "how r you", "kaise ho",
            "kaisa ho", "aap kaise hain", "tum kaise ho",
        )

        identity_markers = (
            "who are you", "tum kaun ho", "aap kaun ho",
            "what are you", "what is sevak", "sevak kya hai",
            "sevak kaun hai",
        )

        capability_markers = (
            "what can you do", "kya kar sakte ho",
            "tum kya kar sakte ho", "aap kya kar sakte ho",
            "capabilities", "features", "help me",
        )

        thanks_markers = (
            "thanks", "thank you", "dhanyavad", "shukriya",
            "thankyou",
        )

        if any(marker in q for marker in greeting_markers):
            return (
                "Namaste! Main SEVAK hoon. Aap mujhse document ke "
                "baare mein voice se sawaal pooch sakte hain. Main "
                "documents ko simple language mein samjhane aur "
                "practical next steps batane mein help karta hoon."
            )

        if any(marker in q for marker in how_are_you_markers):
            return (
                "Main badhiya hoon aur aapki help ke liye ready hoon. "
                "Aap koi document upload karke uske baare mein voice "
                "se sawaal pooch sakte hain."
            )

        if any(marker in q for marker in identity_markers):
            return (
                "Main SEVAK hoon — Voice-First Indian Document Assistant. "
                "Mera kaam confusing documents, notices aur letters ko "
                "simple language mein samjhana aur unke practical next "
                "steps batana hai."
            )

        if any(marker in q for marker in capability_markers):
            return (
                "Main documents ko simple language mein explain kar sakta hoon, "
                "important dates aur amounts identify kar sakta hoon, notice ka "
                "purpose samjha sakta hoon, aur available evidence ke basis par "
                "practical next steps bata sakta hoon."
            )

        if any(marker in q for marker in thanks_markers):
            return (
                "You're welcome! Agar aapke paas koi document hai, upload "
                "kijiye aur uske baare mein mujhse voice mein poochhiye."
            )

        return (
            "Main is sawaal ka reliable answer bina relevant document evidence "
            "ke nahi dena chahta. Aap document upload kijiye, phir main uske "
            "available evidence ke basis par answer aur source information "
            "de sakta hoon."
        )

    evidence = _extract_grounded_evidence(context)

    if not evidence:
        return (
            "Uploaded document mein is question ka clear evidence nahi mila."
        )

    ranked = sorted(
        evidence,
        key=lambda item: _score_evidence(question, item["text"]),
        reverse=True,
    )

    best = ranked[0]
    best_text = best["text"]
    location = best["location"]

    # If there is genuinely no meaningful overlap, do not pretend
    # the document answers the question.
    if _score_evidence(question, best_text) <= 0:
        return (
            "Uploaded document mein is question ka clear evidence nahi mila."
        )

    q = question.lower()
    facts = _extract_key_facts(best_text)

    # ------------------------------------------------------------
    # TARGETED FACT QUESTIONS
    # ------------------------------------------------------------

    if any(
        k in q
        for k in [
            "amount",
            "paise",
            "rupaye",
            "kitna paisa",
            "kitne paise",
        ]
    ):
        if facts:
            answer = (
                f"Document ke according outstanding amount "
                f"{facts[0]} hai."
            )
        else:
            answer = "Document mein amount ka clear figure nahi mila."

    elif any(
        k in q
        for k in [
            "deadline",
            "kab tak",
            "last date",
            "kitne din",
            "days",
            "tarikh",
        ]
    ):
        deadline = next(
            (f for f in facts if "day" in f.lower()),
            None,
        )

        if deadline:
            answer = (
                f"Document ke according required action {deadline} "
                f"ke andar karna hai."
            )
        elif facts:
            answer = f"Document mein date/deadline ke roop mein {facts[0]} diya gaya hai."
        else:
            answer = (
                "Uploaded document mein clear deadline/date ka "
                "usable evidence nahi mila."
            )

    elif any(
        k in q
        for k in [
            "subject",
            "kya notice",
            "notice kya",
            "kis baare",
            "document mein kya",
            "what notice",
        ]
    ):
        # Prefer a sentence containing Subject or Notice.
        subject_match = re.search(
            r"(?i)(?:subject|notice)\s*:\s*([^\n.]+)",
            best_text,
        )

        if subject_match:
            answer = (
                f"Document mein notice ka subject: "
                f"{subject_match.group(1).strip()}."
            )
        else:
            answer = (
                "Document ke according yeh notice "
                f"{best_text[:500].strip()}"
            )

    else:
        # General grounded answer: return the relevant evidence,
        # cleaned and complete enough to be useful.
        answer = (
            "Uploaded document mein relevant information ye hai:\n\n"
            + best_text
        )

    if location:
        answer += f"\n\nSource: {location}."

    return answer


async def _answer_from_evon(
    question: str,
    language: str,
    context: str | None = None,
) -> str:
    """Use Evon when available; otherwise use grounded local fallback."""

    unavailable_markers = [
        "reasoning service is currently unavailable",
        "reasoning service is unavailable",
        "could not complete a grounded analysis",
        "ai reasoning service",
        "service abhi available nahi hai",
        "service abhi unavailable hai",
    ]

    try:
        answer = await evon.ask(
            question=question,
            context=context,
            language=language,
        )

        if answer and not any(
            marker.lower() in answer.lower()
            for marker in unavailable_markers
        ):
            return _clean_grounded_text(answer)

    except Exception:
        pass

    return _local_grounded_answer(
        question=question,
        language=language,
        context=context,
    )


@router.post("/api/ask", tags=["voice"])
async def ask_question(payload: dict) -> dict:
    """Answer a follow-up question using the uploaded document context."""
    question = payload.get("question", "")
    document_id = payload.get("documentId")
    language = payload.get("language", "hinglish")

    if not question or not str(question).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question is required.",
        )

    context = None

    if document_id:
        stored = DOCUMENT_CONTEXT_STORE.get(str(document_id))

        if stored:
            context = stored.get("grounded_context")

    try:
        answer = await _answer_from_evon(
            str(question),
            str(language),
            context=context,
        )
    except Exception:
        answer = _demo_answer(str(question), str(language))

    return {
        "answer": answer,
        "documentId": document_id,
        "response": answer,
        "grounded": bool(context),
    }


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





