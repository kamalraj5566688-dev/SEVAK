"""Pydantic data contracts for the SEVAK backend.

Two families of models live here:

1. *Internal / ingestion models* — DocumentChunk and the raw Evon 30B output
   contract (schema.md).
2. *API response model* — SevakApiResponse, which mirrors the frontend
   TypeScript SevakAnalysisResult type exactly so the React frontend can
   consume the real backend without any client-side transformation.
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# 1. Ingestion chunk model (schema.md §1)
# ---------------------------------------------------------------------------


class DocumentChunk(BaseModel):
    """A single indexed chunk of extracted document text."""

    chunk_id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    page_number: int = Field(ge=1, description="1-indexed page number")
    paragraph_index: int = Field(ge=1, description="1-indexed paragraph within the page")
    raw_text: str = Field(min_length=1)
    confidence_score: float = Field(ge=0.0, le=1.0)

    model_config = ConfigDict(str_strip_whitespace=True)


# ---------------------------------------------------------------------------
# 2. Evon 30B raw output contract (schema.md §3)
# ---------------------------------------------------------------------------


class CitationItem(BaseModel):
    claim: str = Field(min_length=1)
    source_location: str = Field(min_length=1)


class DeadlineItem(BaseModel):
    action: str = Field(min_length=1)
    timeline: str = Field(min_length=1)
    source_page: int = Field(ge=1)


SeverityLevel = Literal["GREEN", "YELLOW", "RED"]


class EvonAnalysisResult(BaseModel):
    """Raw structured output produced by the Evon 30B reasoning engine."""

    document_type: Optional[str] = Field(
        default=None,
        description="Model-detected document type (confirmation signal, not primary).",
    )
    severity: SeverityLevel
    severity_reason: str
    what: str
    why: str
    next_steps: List[str] = Field(min_length=3, max_length=3)
    rights_and_protections: str
    deadlines: List[DeadlineItem] = Field(default_factory=list)
    citations: List[CitationItem] = Field(default_factory=list)
    spoken_summary_regional: str

    @field_validator("next_steps")
    @classmethod
    def _exactly_three(cls, v: List[str]) -> List[str]:
        if len(v) != 3:
            raise ValueError("next_steps must contain exactly 3 items")
        return v

    model_config = ConfigDict(str_strip_whitespace=True)


# ---------------------------------------------------------------------------
# 3. Frontend-compatible API response (mirrors src/types/index.ts)
# ---------------------------------------------------------------------------


Category = Literal[
    "Traffic Police Notice",
    "Banking & KYC",
    "Income Tax Department",
    "Government Notice",
    "Legal Summons",
    "Unrecognized / Not a Document",
]

UrgencyLevel = Literal["high", "medium", "low"]


class WhatBlock(BaseModel):
    summary: str
    details: str


class WhyBlock(BaseModel):
    significance: str
    urgency_reason: str


class NextStepItem(BaseModel):
    step: int
    title: str
    description: str
    action_url: Optional[str] = None


class RightsBlock(BaseModel):
    title: str
    safeguards: List[str]
    disclaimer: str


class DeadlineBlock(BaseModel):
    has_deadline: bool
    date: Optional[str] = None
    days_remaining: Optional[int] = None
    urgency_level: Optional[UrgencyLevel] = None
    consequence_text: Optional[str] = None


class SourceBlock(BaseModel):
    issuing_authority: str
    legal_section: str
    reference_number: str
    official_portal_url: Optional[str] = None


class SevakApiResponse(BaseModel):
    """Full analysis payload returned by POST /api/analyze-document.

    Shape is identical to the frontend SevakAnalysisResult TypeScript type so
    the API client can spread the result directly into the ResultsView.
    """

    id: str
    document_title: str
    category: Category
    original_file_name: str
    file_size: str
    file_type: str
    upload_date: str
    confidence_score: float
    classification_confidence: float = 0.0
    is_demo_fallback: bool = False

    what: WhatBlock
    why: WhyBlock
    next_steps: List[NextStepItem] = Field(min_length=3, max_length=3)
    rights: RightsBlock
    deadline: DeadlineBlock
    source: SourceBlock
    voice_summaries: Dict[str, str]
    audio_base64: Optional[str] = None
    citations: List[CitationItem] = Field(default_factory=list)

    @field_validator("next_steps")
    @classmethod
    def _exactly_three_steps(cls, v: List[NextStepItem]) -> List[NextStepItem]:
        if len(v) != 3:
            raise ValueError("next_steps must contain exactly 3 items")
        return v

    model_config = ConfigDict(
        str_strip_whitespace=True,
        populate_by_name=True,
    )
