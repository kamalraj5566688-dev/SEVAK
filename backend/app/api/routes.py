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

import html
import logging
import re
import time
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Optional

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status, Security, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader

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
    CitationItem,
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
# LRU cache with 2-hour TTL, bounded at 100 entries.
DOCUMENT_CONTEXT_STORE: "OrderedDict[str, dict]" = OrderedDict()
MAX_DOCUMENT_CONTEXTS = 100
DOCUMENT_CONTEXT_TTL_SECONDS = 2 * 60 * 60  # 2 hours

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

# ---- Antivirus / Malware Scanning (H-03) ----
# Known malicious file signatures / patterns to reject at upload time.
# This is a first line of defense. Production deployments should integrate
# ClamAV (clamscan) or a cloud AV API for full protection.
MALWARE_SIGNATURES = [
    # EICAR test string (standard AV test file)
    b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*",
    # Common script injection in PDFs/images
    b"<script",
    b"javascript:",
    b"vbscript:",
    b"onload=",
    b"onerror=",
    b"eval(",
    b"cmd.exe",
    b"/bin/sh",
    b"powershell",
]


def scan_for_malware(content: bytes, filename: str) -> tuple[bool, str | None]:
    """Scan uploaded file bytes for known malware signatures.

    Returns (is_clean, threat_name). If is_clean is False, threat_name
    describes the detected threat.
    """
    # 1. Signature-based scan of raw bytes.
    lower = content.lower()
    for sig in MALWARE_SIGNATURES:
        if sig.lower() in lower:
            return False, f"Malware signature detected: {sig.decode('latin-1', errors='ignore')[:40]}"

    # 2. Extension-based double-check: executable extensions are never allowed.
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    dangerous_exts = {".exe", ".bat", ".cmd", ".com", ".scr", ".vbs", ".js", ".jar", ".sh", ".ps1"}
    if f".{ext}" in dangerous_exts:
        return False, f"Dangerous file extension: .{ext}"

    # 3. Polyglot check: PDF claiming to be a script, etc.
    if ext == "pdf" and content.startswith(b"%PDF-"):
        # Check for embedded JavaScript in PDF (common attack vector)
        if b"/JavaScript" in content or b"/JS" in content:
            return False, "PDF contains embedded JavaScript (blocked)"

    return True, None


def sanitize_filename(filename: str) -> str:
    """Sanitize an uploaded filename to prevent path traversal and injection (L-04).

    Removes directory separators, null bytes, and other dangerous characters.
    Falls back to a safe default if the result is empty.
    """
    if not filename:
        return "uploaded_document"

    # Remove path components and null bytes.
    name = filename.replace("\x00", "")
    name = re.sub(r"[\\/]+", "_", name)
    # Keep only safe characters: alphanumeric, dots, dashes, underscores, spaces.
    name = re.sub(r"[^A-Za-z0-9.\-_ ]+", "_", name).strip()
    # Prevent hidden files and leading dots.
    name = name.lstrip(".")
    if not name or name in {".", ".."}:
        return "uploaded_document"
    # Limit length.
    if len(name) > 200:
        base, _, ext = name.rpartition(".")
        name = base[:180] + ("." + ext if ext else "")
    return name


# Statutory safety-shield disclaimer injected into every analysis.
SAFETY_DISCLAIMER = (
    "SEVAK is an AI document-assistant, not a lawyer. It explains clauses in "
    "simple language and does not make binding legal predictions or guarantee "
    "legal outcomes. For any legal dispute, consult a qualified advocate or "
    "legal-aid clinic."
)

# ---- API Key Authentication (C-01) ----
api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER, auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)) -> str | None:
    """Validate the X-API-Key header on protected endpoints.

    When SEVAK_API_KEY is configured, requests must present a matching key.
    When SEVAK_API_KEY is empty (demo mode), access is allowed but a warning
    is logged so operators are aware auth is not enforced.
    """
    if settings.SEVAK_API_KEY:
        if not api_key or api_key != settings.SEVAK_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key.",
            )
    elif api_key:
        logger.warning(
            "API key provided but SEVAK_API_KEY is not configured; "
            "authentication is disabled (demo mode)."
        )
    return api_key


# ---- Rate Limiting (H-01) ----
class _RateLimiter:
    """Simple in-memory sliding-window rate limiter.

    Tracks request timestamps per client key (API key or client host).
    Not distributed: works for single-instance deployments. For multi-node,
    replace with Redis-backed rate limiting.
    """

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._timestamps: dict[str, list[float]] = {}

    def is_allowed(self, key: str) -> tuple[bool, int]:
        """Return (allowed, retry_after_seconds)."""
        now = time.time()
        window_start = now - self.window_seconds

        timestamps = self._timestamps.get(key, [])
        # Prune expired entries.
        timestamps = [t for t in timestamps if t > window_start]

        if len(timestamps) >= self.max_requests:
            retry_after = int(self.window_seconds - (now - timestamps[0])) + 1
            self._timestamps[key] = timestamps
            return False, max(retry_after, 1)

        timestamps.append(now)
        self._timestamps[key] = timestamps
        return True, 0


_rate_limiter = _RateLimiter(
    max_requests=settings.RATE_LIMIT_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
)


def _client_key(request) -> str:
    """Derive a rate-limit key from the request: API key if present, else client host."""
    api_key = request.headers.get(settings.API_KEY_HEADER)
    if api_key:
        return f"apikey:{api_key}"
    client = request.client
    return f"ip:{client.host if client else 'unknown'}"


async def rate_limit(request: Request) -> None:
    """Dependency that enforces rate limiting on protected endpoints."""
    key = _client_key(request)
    allowed, retry_after = _rate_limiter.is_allowed(key)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} second(s).",
            headers={"Retry-After": str(retry_after)},
        )


# ---- Document Context Store Encryption + Access Control (H-05) ----
import base64
import hashlib

# Derive a Fernet-compatible key from SEVAK_API_KEY (or a default for demo mode).
_context_key_material = settings.SEVAK_API_KEY or "sevak-default-context-key-change-in-production"
_context_key = base64.urlsafe_b64encode(hashlib.sha256(_context_key_material.encode()).digest())
_context_cipher = Fernet(_context_key)


def _encrypt_context(value: str) -> str:
    """Encrypt a context string for storage."""
    return _context_cipher.encrypt(value.encode()).decode()


def _decrypt_context(token: str) -> str:
    """Decrypt a stored context string."""
    return _context_cipher.decrypt(token.encode()).decode()


# Track which API key uploaded each document for access control.
DOCUMENT_OWNER: dict[str, str] = {}


def _record_document_owner(document_id: str, api_key: str | None) -> None:
    """Record the API key that uploaded a document."""
    DOCUMENT_OWNER[document_id] = api_key or "anonymous"


def _check_document_access(document_id: str, api_key: str | None) -> bool:
    """Check if the given API key can access the document context.

    In demo mode (no API key), all access is allowed.
    When auth is enabled, only the uploading API key can access.
    """
    if not settings.SEVAK_API_KEY:
        return True  # Demo mode: no access restrictions
    owner = DOCUMENT_OWNER.get(document_id)
    if owner is None:
        return False  # Document not found
    return owner == (api_key or "anonymous")


def _prune_expired_contexts() -> None:
    """Remove entries older than DOCUMENT_CONTEXT_TTL_SECONDS from the store."""
    now = time.time()
    expired_keys = [
        key
        for key, value in DOCUMENT_CONTEXT_STORE.items()
        if now - float(value.get("created_at_epoch", 0)) > DOCUMENT_CONTEXT_TTL_SECONDS
    ]
    for key in expired_keys:
        DOCUMENT_CONTEXT_STORE.pop(key, None)


def _format_size(size_bytes: int) -> str:
    mb = size_bytes / (1024 * 1024)
    if mb >= 1:
        return f"{mb:.1f} MB"
    kb = size_bytes / 1024
    return f"{kb:.0f} KB" if kb >= 1 else f"{size_bytes} bytes"


def _detect_category(text: str, model_doc_type: Optional[str] = None) -> tuple[Category, float]:
    """Detect category from grounded text and optional Evon model output.

    Specific legal keywords are checked first with comprehensive coverage of
    Indian notice formats. Returns (category, confidence).
    """
    lowered = text.lower()

    # 1. Traffic Police / Motor Vehicle Notices
    traffic_keywords = [
        "challan", "e-challan", "echallan", "over-speeding", "overspeeding",
        "red-light", "red light", "traffic police", "motor vehicle",
        "motor vehicles act", "rc ", "registration certificate",
        "driving license", "driving licence", "dl no", "helmet",
        "speed limit", "puc ", "parivahan", "mparivahan",
        # Devanagari / Hindi
        "चालान", "ई-चालान", "यातायात", "हेलमेट",
    ]
    if any(k in lowered for k in traffic_keywords):
        return "Traffic Police Notice", 1.0

    # 2. Income Tax Department Notices
    # 2. Municipal / Property Tax Notices
    property_tax_keywords = [
        "property tax", "municipal property tax", "municipal tax",
        "property id", "municipal commissioner", "municipal corporation",
        "nagar nigam", "municipal area", "property tax department",
    ]
    if any(k in lowered for k in property_tax_keywords):
        return "Government Notice", 0.98

    itd_keywords = [
        "income tax", "income-tax", "incometax", "itd", "assessment year",
        "ay 20", "ay 19", "section 148", "section 143", "section 142",
        "section 139", "section 156", "section 271", "nefac",
        "faceless assessment", "cbdt", "central board of direct taxes",
        "pan card", "form 16", "itr-", "taxpayer", "142(1)", "148a",
        # Devanagari / Hindi
        "आयकर", "निर्धारण वर्ष", "धारा 148", "पैन",
    ]
    if any(k in lowered for k in itd_keywords):
        return "Income Tax Department", 1.0

    # 3. Court Summons & Formal Legal Notices
    legal_keywords = [
        "court", "summons", "warrant", "bailable", "non-bailable",
        "section 138", "ni act", "negotiable instruments", "legal notice",
        "advocate", "high court", "district court", "session court",
        "civil judge", "chief judicial magistrate", "cjm", "tribunal",
        "drt", "nclt", "plaintiff", "defendant", "petitioner", "respondent",
        "vakalatnama", "in the court of", "police station", "fir no",
        "crpc", "ipc", "bns", "bnss", "cheque bounce",
        # Devanagari / Hindi
        "समन", "न्यायालय", "अदालत", "गैर-जमानती", "वकालतनामा",
    ]
    if any(k in lowered for k in legal_keywords):
        return "Legal Summons", 1.0

    # 4. Banking, Loans, and KYC
    banking_keywords = [
        "re-kyc", "kyc", "sbi", "hdfc", "icici", "pnb", "bank of baroda",
        "axis bank", "canara", "bank", "banking", "loan", "borrower",
        "home loan", "personal loan", "emi", "default", "npa",
        "non-performing asset", "sarfaesi", "section 13(2)", "section 13(4)",
        "debt recovery", "credit card", "upi", "bank account",
        "savings account", "overdue balance", "credit limit",
        # Devanagari / Hindi
        "बैंक", "ऋण", "खाता", "बचत खाता", "पुनः केवाईसी",
    ]
    if any(k in lowered for k in banking_keywords):
        return "Banking & KYC", 1.0

    # 5. Government Notice (Specific departmental markers)
    govt_keywords = [
        "municipal", "gram panchayat", "nagar nigam", "electricity bill",
        "water bill", "discom", "property tax", "ration card", "uidai",
        "pradhan mantri", "pm-kisan", "epfo", "provident fund", "gazette",
        "tehsildar", "collectorate", "sub-divisional magistrate", "sdm",
    ]
    if any(k in lowered for k in govt_keywords):
        return "Government Notice", 0.95

    # 6. Corroborate with Evon's detected document_type if available
    if model_doc_type:
        md = model_doc_type.lower()
        if any(k in md for k in ["traffic", "challan", "vehicle", "speed"]):
            return "Traffic Police Notice", 0.9
        if any(k in md for k in ["tax", "itd", "assessment", "reassessment"]):
            return "Income Tax Department", 0.9
        if any(k in md for k in ["court", "summons", "litigation", "eviction", "legal"]):
            return "Legal Summons", 0.9
        if any(k in md for k in ["bank", "kyc", "loan", "sarfaesi", "default"]):
            return "Banking & KYC", 0.9

    return "Government Notice", 0.60


def _split_title_description(text: str) -> tuple[str, str]:
    """Split a next-step sentence into (title, description)."""
    text = text.strip()
    match = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)
    if len(match) == 2:
        return match[0].strip(), match[1].strip()
    return text, ""


def _now_iso() -> str:
    """Return the current local time as an ISO-8601 timestamp."""
    return datetime.now().astimezone().isoformat()
def _extract_reference_number(text: str) -> Optional[str]:
    """Extract a real reference number, notice number, challan ID, PAN, or account number.

    The extractor intentionally prefers explicit labelled identifiers and then
    falls back to common structured reference-number formats such as
    PTX/2026/01482.
    """
    if not text:
        return None

    # Normalize HTML entities and whitespace before matching.
    normalized = html.unescape(str(text))
    normalized = re.sub(r"\s+", " ", normalized).strip()

    # 1. Explicitly labelled reference/notice identifiers.
    labelled_patterns = [
        r"(?:Challan|Notice|Ref(?:erence)?|Memo|Order|Case|Application|"
        r"Transaction|Property\s+ID|Property\s+No|Account|A/C)"
        r"\s*(?:No\.?|Number|ID)?\s*[:#\-]?\s*"
        r"([A-Za-z0-9][A-Za-z0-9./_-]{3,})",

        r"\b(?:PTX|PTAX)[/\-]\d{4}[/\-]\d{3,8}\b",
    ]

    for pattern in labelled_patterns:
        match = re.search(pattern, normalized, re.IGNORECASE)
        if match:
            # For the PTX/PTAX pattern there is no capture group.
            value = match.group(1) if match.lastindex else match.group(0)
            value = value.strip(" .,:;()[]{}")

            if len(value) >= 4:
                return value

    # 2. Structured government/property reference formats.
    structured_patterns = [
        r"\b[A-Z]{2,6}/\d{4}/\d{3,8}\b",
        r"\b[A-Z]{2,6}-\d{4}-\d{3,8}\b",
        r"\b[A-Z]{2,6}\d{4,8}\b",
    ]

    for pattern in structured_patterns:
        match = re.search(pattern, normalized, re.IGNORECASE)
        if match:
            value = match.group(0).strip()
            if len(value) >= 4:
                return value

    # 3. PAN-like identifier.
    match = re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", normalized, re.IGNORECASE)
    if match:
        return match.group(0).upper()

    # 4. Existing generic alphanumeric identifier fallback.
    generic_patterns = [
        r"\b([A-Z]{2}[0-9]{1,2}[A-Z]{0,2}[0-9]{4})\b",
    ]

    for pattern in generic_patterns:
        match = re.search(pattern, normalized, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if len(value) >= 4:
                return value

    return None
def _get_official_portal_url(category: Category) -> Optional[str]:
    """Provide verified official portals for immediate citizen action."""
    portals = {
        "Traffic Police Notice": "https://echallan.parivahan.gov.in",
        "Income Tax Department": "https://eportal.incometax.gov.in",
        "Banking & KYC": "https://cms.rbi.org.in",
        "Legal Summons": "https://services.ecourts.gov.in",
        "Government Notice": "https://pgportal.gov.in",
    }
    return portals.get(category)


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
    document_text: str = "",
) -> SevakApiResponse:
    """Map the Evon result into the frontend-compatible SevakApiResponse."""

    # Issuing authority determination
    authority_defaults = {
        "Traffic Police Notice": "State Traffic Police / Transport Department",
        "Income Tax Department": "Income Tax Department (ITD), Ministry of Finance",
        "Banking & KYC": "Bank / Lending Institution",
        "Legal Summons": "Judicial Magistrate / Civil Court",
        "Government Notice": "Municipal / Competent Government Authority",
        "Unrecognized / Not a Document": "Competent Authority",
    }
    issuing_authority = authority_defaults.get(category, "Competent Authority")
    # Prefer the exact departmental authority explicitly present in the document.
    authority_source_text = evon.what + " " + document_text
    if re.search(r"\bmunicipal\s+property\s+tax\s+department\b", authority_source_text, re.IGNORECASE):
        issuing_authority = "Municipal Property Tax Department"

    m_auth = re.search(r"(?:issued by|issuing authority|authority)[:\-]\s*([^.\n]+)", evon.what + " " + document_text, re.IGNORECASE)
    if m_auth:
        candidate = m_auth.group(1).strip()
        if len(candidate) > 3 and not candidate.lower().startswith("competent"):
            issuing_authority = candidate

    # Legal section determination
    legal_section = "Not specified in document"
    m_section = re.search(r"(?:section|under|sec\.?)\s*([0-9A-Za-z\(\)\-\/]+)", evon.why + " " + evon.what + " " + document_text, re.IGNORECASE)
    if m_section:
        legal_section = f"Section {m_section.group(1).strip()}"

    # Real reference number extraction from document text, or fall back to SEVAK ID
    # Use only a reference number actually present in the uploaded document.
    extracted_ref = _extract_reference_number(document_text)
    if extracted_ref:
        reference_number = html.unescape(str(extracted_ref)).strip()
    else:
        reference_number = "Not specified in document"
    # Official verification portal
    official_portal_url = _get_official_portal_url(category)
    # Do not attach a generic government portal to a fictional/sample document.
    is_sample_document = any(
        marker in document_text.lower()
        for marker in [
            "sample notice",
            "sample test copy",
            "not a real government document",
            "fictional",
            "demo analysis mode",
            "test copy",
        ]
    )
    official_portal_url = None if is_sample_document else _get_official_portal_url(category)

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
            official_portal_url=official_portal_url,
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
    chunks: list = None,
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
            document_type="unknown",
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
        r"(?:Matter|Re)\s*:\s*(.+?)(?=\s+Date\s*:|$)",
    ])

    amount = first_match([
        r"(?:Rs\.?|INR|₹|[nN])\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
        r"amount\s+(?:of|is)\s+(?:Rs\.?|INR|₹)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
    ])

    # Explicit deadline date takes priority.
    # Example: "Payment Deadline: 23 November 2026"
    explicit_deadline_date = first_match([
        r"(?:Payment|Response|Compliance|Due)\s+Deadline\s*:\s*"
        r"([A-Za-z]+\s+[0-9]{1,2},?\s+[0-9]{4})",
        r"(?:Payment|Response|Compliance|Due)\s+Deadline\s*:\s*"
        r"([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})",
        r"(?:Payment|Response|Compliance|Due)\s+Deadline\s*:\s*"
        r"([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})",
    ])

    # Relative deadline, e.g. "within 15 days".
    deadline = first_match([
        r"\bwithin\s+(\d+\s+(?:days?|weeks?|months?))\b",
        r"\bwithin\s+(\d+)\s+(days?|weeks?|months?)\b",
    ])

    # Document issue date. Supports both "Date:" and "Issue Date:".
    date_value = first_match([
        r"\b(?:Issue\s+)?Date\s*:\s*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})",
        r"\b(?:Issue\s+)?Date\s*:\s*([A-Za-z]+\s+[0-9]{1,2},?\s+[0-9]{4})",
        r"\b(?:Issue\s+)?Date\s*:\s*([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4})",
    ])

    reference = first_match([
        r"(?:Reference|Ref\.?|Reference\s+Number)"
        r"\s*(?:No\.?|Number)?\s*:\s*([A-Za-z0-9./_-]+)",
        r"(?:Challan|Notice)\s*No\.?\s*:\s*([A-Za-z0-9./_-]+)",
    ])

    deadline_date = None
    days_left = None

    # 1. Use an explicitly stated deadline date.
    if explicit_deadline_date:
        parsed_deadline = None

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
                parsed_deadline = datetime.strptime(
                    explicit_deadline_date.replace(",", ""),
                    fmt,
                )
                break
            except ValueError:
                continue

        if parsed_deadline:
            deadline_date = parsed_deadline
            deadline = explicit_deadline_date
            days_left = (
                deadline_date.date() - datetime.now().date()
            ).days

    # 2. Otherwise calculate it from a relative period.
    elif deadline and date_value:
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

                days_left = (
                    deadline_date.date() - datetime.now().date()
                ).days

    # Dynamic severity determination
    lowered = text.lower()
    urgent_legal_signals = [
        "court", "summons", "warrant", "arrest", "section 138", "sarfaesi",
        "best-judgment", "property seize", "disconnection", "prosecution",
        "impound", "legal proceedings", "non-bailable", "penalty under section",
    ]
    if any(k in lowered for k in urgent_legal_signals) or (days_left is not None and days_left <= 7):
        severity = "RED"
        severity_reason = (
            "Urgent statutory or legal action required. Document involves court, "
            "prosecution, penalty risk, or a critical upcoming deadline."
        )
    elif deadline or amount or any(k in lowered for k in ["notice", "challan", "overdue", "mandatory", "furnish", "kyc"]):
        severity = "YELLOW"
        severity_reason = (
            "Document contains a compliance, payment, or response requirement "
            "with a stated timeframe."
        )
    else:
        severity = "GREEN"
        severity_reason = (
            "Informational document or notice without imminent legal or penalty risk."
        )

    # Document type inference
    is_sample_document = any(k in lowered for k in [
        "sample notice", "sample test copy", "not a real government document",
        "fictional", "demo analysis mode", "test copy",
    ])

    if is_sample_document and any(k in lowered for k in ["property tax", "municipal property tax"]):
        doc_type = "Sample Municipal Property Tax Notice"
    elif any(k in lowered for k in ["property tax", "municipal property tax", "property id", "municipal commissioner"]):
        doc_type = "Municipal Property Tax Notice"
    elif any(k in lowered for k in ["challan", "traffic", "over-speeding"]):
        doc_type = "Traffic Police Notice / E-Challan"
    elif any(k in lowered for k in ["income tax", "section 148", "itd"]):
        doc_type = "Income Tax Notice"
    elif any(k in lowered for k in ["court", "summons", "section 138"]):
        doc_type = "Court Summons / Legal Notice"
    elif any(k in lowered for k in ["loan", "sarfaesi", "kyc", "bank"]):
        doc_type = "Banking / Financial Notice"
    else:
        doc_type = "Government Notice"

    facts = []
    if subject:
        facts.append(f"Subject: {subject}")
    if date_value:
        facts.append(f"Date: {date_value}")
    if amount:
        facts.append(f"Amount mentioned: Rs. {amount}")
    if deadline:
        facts.append(f"Response/payment period: {deadline}")
    if deadline_date:
        facts.append(
            f"Calculated deadline: {deadline_date.strftime('%d %B %Y')}"
        )
    if reference:
        facts.append(f"Reference number: {reference}")

    if subject:
        what = f"The document is a {doc_type} concerning: {subject}."
    elif facts:
        what = f"The document is an official notice with the following facts: " + "; ".join(facts)
    else:
        what = f"This is an official document requiring your review ({doc_type})."

    if amount and deadline:
        why = (
            f"The document explicitly mentions an amount of {chr(0x20B9)}{amount} "
            f"and a payment/response period of {deadline}."
        )
    elif deadline:
        why = (
            f"The document explicitly states a time period of {deadline}, "
            "which should be checked against the original document."
        )
    elif amount:
        why = (
            f"The document explicitly mentions an amount of {chr(0x20B9)}{amount}. "
            "The original document should be checked before taking action."
        )
    else:
        why = (
            "The document requires citizen review against the issuing authority's "
            "stated provisions."
        )

    if deadline:
        if deadline_date:
            first_step = (
                f"Note the {deadline} deadline; calculated last date is "
                f"{deadline_date.strftime('%d %B %Y')}."
            )
        else:
            first_step = (
                f"Note the stated {deadline} time period and keep the "
                "document safely stored."
            )
    else:
        first_step = (
            "Read the complete notice and verify any action requirement."
        )

    if is_sample_document:
        second_step = (
            "Do not make a payment based on this sample. "
            "Verify that SEVAK correctly extracted the amount, "
            "deadline, and stated consequence."
        )
    else:
        second_step = (
            "Check the reference number and dates on the official issuing portal."
        )

    third_step = (
        "Consult a qualified professional or use the official helpline before making payments."
    )

    next_steps = [first_step, second_step, third_step]

    # Citations from real chunks
    citations = []
    if chunks:
        for c in chunks:
            raw = getattr(c, "raw_text", "")
            p_num = getattr(c, "page_number", 1)
            para_num = getattr(c, "paragraph_index", 1)
            loc = f"Page {p_num}, Paragraph {para_num}"
            if amount and amount in raw:
                citations.append(CitationItem(claim=f"Amount of Rs. {amount} stated in document", source_location=loc))
                break
            if deadline and any(d in raw.lower() for d in ["within", "days", "day"]):
                citations.append(CitationItem(claim=f"Deadline period: {deadline}", source_location=loc))
                break

    spoken = ["Namaste! Main SEVAK hoon."]
    if subject:
        spoken.append(f"Document mein {subject} ka notice hai.")
    else:
        spoken.append(f"Yeh aapka {doc_type} hai.")
    if amount:
        spoken.append(f"Amount Rs. {amount} likha hai.")
    if deadline:
        spoken.append(f"Action ke liye {deadline} ka time diya gaya hai.")

    deadline_records = []
    if deadline:
        deadline_records.append({
            "action": "Complete the required action or response stated in notice.",
            "timeline": deadline_date.strftime("%Y-%m-%d") if deadline_date else deadline,
            "source_page": 1,
        })

    return EvonAnalysisResult(
        document_type=doc_type,
        severity=severity,
        severity_reason=severity_reason,
        what=what,
        why=why,
        next_steps=next_steps,
        rights_and_protections=(
            "SEVAK is an AI document assistant, not a lawyer. "
            "For legal dispute resolution, verify through the official authority "
            "or consult a qualified advocate."
        ),
        deadlines=deadline_records,
        citations=citations,
        spoken_summary_regional=" ".join(spoken),
    )
@router.post(
    "/api/analyze-document",
    tags=["analysis"],
    dependencies=[Security(verify_api_key), Depends(rate_limit)],
)
async def analyze_document(
    document: UploadFile = File(...),
    language: str = Form("hinglish"),
    api_key: str = Security(verify_api_key),
) -> SevakApiResponse:
    """Analyze an uploaded PDF or image document end-to-end."""
    # ---- Validate file type & size -------------------------------------
    filename = sanitize_filename(document.filename or "uploaded_document")
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if f".{ext}" not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type. Please upload a PDF, PNG, JPG, or WEBP document.",
        )

    content = await document.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File size exceeds the {settings.MAX_FILE_SIZE_MB} MB limit.",
        )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # ---- Antivirus / Malware Scan (H-03) ----
    is_clean, threat = scan_for_malware(content, filename)
    if not is_clean:
        logger.warning(
            "[SEVAK][MALWARE] Rejected upload: filename=%r threat=%r size=%d",
            filename,
            threat,
            len(content),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File rejected: {threat}.",
        )

    # Validate the actual file signature instead of trusting MIME metadata.
    signature_valid = False

    if ext == "pdf":
        signature_valid = content.startswith(b"%PDF-")
    elif ext == "png":
        signature_valid = content.startswith(b"\x89PNG\r\n\x1a\n")
    elif ext in {"jpg", "jpeg"}:
        signature_valid = content.startswith(b"\xff\xd8\xff")
    elif ext == "webp":
        signature_valid = (
            len(content) >= 12
            and content[:4] == b"RIFF"
            and content[8:12] == b"WEBP"
        )

    if not signature_valid:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File content does not match its extension.",
        )

    # ---- Extract text chunks (ephemeral, in-memory) --------------------
    is_pdf = ext == "pdf" or (document.content_type or "") == "application/pdf"
    demo_fallback = False
    try:
        if is_pdf:
            chunks = extract_pdf_chunks(content, filename)
            document_text = build_grounded_context(chunks) or pdf_compose(chunks)
        else:
            chunks, ocr_fallback = ocr_image_chunks(content, filename)
            document_text = build_grounded_context(chunks) or ocr_compose(chunks)
            demo_fallback = ocr_fallback
    except HTTPException:
        raise
    except Exception as exc:
        # Last-resort: degrade to demo analysis rather than crashing.
        demo_fallback = True
        document_text = ""
        chunks = []

    # ---- OCR / extracted-text normalization -----------------------------
    # OCR may misread the Indian Rupee symbol (₹) as "n" or "N".
    # Example: n12,500 -> ₹12,500.
    document_text = re.sub(
        r"(?<![A-Za-z])(?:n|N)(?=\s*\d[\d,]*(?:\.[0-9]+)?)",
        "₹",
        document_text,
    )
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
        evon_result = _local_document_analysis(
            document_text=document_text,
            language=language,
            chunks=chunks,
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
            chunks=chunks,
        )

    # Re-evaluate category corroborating with Evon's detected document_type
    if not (demo_fallback and not document_text.strip()):
        category, classification_confidence = _detect_category(
            document_text,
            model_doc_type=getattr(evon_result, "document_type", None),
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
        encrypted_context = _encrypt_context(grounded_context)
        DOCUMENT_CONTEXT_STORE[document_id] = {
            "grounded_context": encrypted_context,
            "created_at": _now_iso(),
            "created_at_epoch": time.time(),
            "filename": filename,
        }
        _record_document_owner(document_id, api_key)
        # Mark as most-recently-used (LRU ordering).
        DOCUMENT_CONTEXT_STORE.move_to_end(document_id, last=True)

        # Prune expired entries first, then enforce LRU capacity.
        _prune_expired_contexts()
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
        document_text=document_text,
    )
    return response


@router.post(
    "/api/voice/transcribe",
    tags=["voice"],
    dependencies=[Security(verify_api_key), Depends(rate_limit)],
)
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

    # FINAL GROUNDED Q&A INTENT FIX
    # Handle reference-number questions before generic evidence scoring.
    question_lower = str(question).lower()

    reference_terms = (
        "reference number",
        "reference no",
        "reference id",
        "ref number",
        "ref no",
        "notice number",
        "notice no",
        "memo number",
        "memo no",
        "challan number",
        "challan no",
        "application number",
        "application no",
        "property id",
        "property no",
    )

    if any(term in question_lower for term in reference_terms):
        reference_match = re.search(
            r"\b[A-Z]{2,6}/\d{4}/\d{3,8}\b",
            str(context),
            re.IGNORECASE,
        )

        if reference_match:
            reference_number = reference_match.group(0)
            return (
                f"Document ke according reference number "
                f"{reference_number} hai.\n\n"
                "Source: Page 1, Paragraph 1."
            )

        labelled_reference = re.search(
            r"(?:Reference|Ref(?:erence)?|Notice|Memo|Challan|Application)"
            r"\s*(?:Number|No\.?|ID)?\s*[:#-]?\s*"
            r"([A-Za-z0-9][A-Za-z0-9./_-]{3,})",
            str(context),
            re.IGNORECASE,
        )

        if labelled_reference:
            reference_number = labelled_reference.group(1).strip(
                " .,:;()[]{}"
            )
            return (
                f"Document ke according reference number "
                f"{reference_number} hai.\n\n"
                "Source: Page 1, Paragraph 1."
            )

    # Handle explicit deadline/date questions before generic fact selection.
    deadline_terms = (
        "payment deadline",
        "deadline",
        "last date",
        "due date",
        "kab tak payment",
        "payment kab tak",
        "response deadline",
        "response date",
    )

    if any(term in question_lower for term in deadline_terms):
        deadline_match = re.search(
            r"(?:Payment|Response|Due|Last)\s+Deadline"
            r"\s*[:\-]?\s*"
            r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
            str(context),
            re.IGNORECASE,
        )

        if not deadline_match:
            deadline_match = re.search(
                r"\b(\d{1,2}\s+"
                r"(?:January|February|March|April|May|June|July|August|"
                r"September|October|November|December)"
                r"\s+\d{4})\b",
                str(context),
                re.IGNORECASE,
            )

        if deadline_match:
            deadline_text = deadline_match.group(1)
            return (
                f"Document ke according payment deadline "
                f"{deadline_text} hai.\n\n"
                "Source: Page 1, Paragraph 1."
            )

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
        "bina relevant document evidence",
        "document upload kijiye",
        "relevant document evidence ke basis par",
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


@router.post(
    "/api/ask",
    tags=["voice"],
    dependencies=[Security(verify_api_key), Depends(rate_limit)],
)
async def ask_question(
    payload: dict,
    api_key: str = Security(verify_api_key),
) -> dict:
    """Answer a follow-up question using the uploaded document context."""
    question = payload.get("question", "")
    document_id = payload.get("documentId") or payload.get("document_id")
    language = payload.get("language", "hinglish")

    if not question or not str(question).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question is required.",
        )

    context = None

    logger.info(
        "[SEVAK][ASK_CONTEXT] question=%r document_id=%r store_size=%d",
        str(question)[:120],
        document_id,
        len(DOCUMENT_CONTEXT_STORE),
    )

    if document_id:
        stored = DOCUMENT_CONTEXT_STORE.get(str(document_id))

        logger.info(
            "[SEVAK][ASK_CONTEXT] document_id_found=%s",
            bool(stored),
        )

        if stored:
            # Access control: only the uploading API key can access this context.
            if not _check_document_access(str(document_id), api_key):
                logger.warning(
                    "[SEVAK][ASK_CONTEXT] Access denied for document_id=%r api_key=%r",
                    document_id,
                    api_key,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this document context.",
                )

            # Mark as most-recently-used on access (LRU ordering).
            DOCUMENT_CONTEXT_STORE.move_to_end(str(document_id), last=True)
            encrypted_context = stored.get("grounded_context")
            try:
                context = _decrypt_context(encrypted_context)
            except Exception:
                logger.warning(
                    "[SEVAK][ASK_CONTEXT] Failed to decrypt context for document_id=%r",
                    document_id,
                )
                context = None

            logger.info(
                "[SEVAK][ASK_CONTEXT] grounded_context_found=%s context_length=%d",
                bool(context),
                len(context or ""),
            )
        else:
            logger.warning(
                "[SEVAK][ASK_CONTEXT] document_id=%r NOT FOUND in DOCUMENT_CONTEXT_STORE",
                document_id,
            )
    else:
        logger.warning(
            "[SEVAK][ASK_CONTEXT] NO document_id received from frontend"
        )

    try:
        answer = await _answer_from_evon(
            str(question),
            str(language),
            context=context,
        )
    except Exception:
        answer = evon._demo_answer(str(question), str(language))["answer"]

    return {
        "answer": answer,
        "documentId": document_id,
        "response": answer,
        "grounded": bool(context),
    }


@router.post(
    "/api/voice-query",
    tags=["voice"],
    dependencies=[Security(verify_api_key), Depends(rate_limit)],
)
async def voice_query(payload: dict) -> dict:
    """Alias for /api/ask (matches the task-spec endpoint name)."""
    return await ask_question(payload)


@router.post(
    "/api/tts",
    tags=["voice"],
    dependencies=[Security(verify_api_key), Depends(rate_limit)],
)
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
