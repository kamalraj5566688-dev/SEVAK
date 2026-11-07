"""PDF text extraction engine using pdfplumber (primary) and pypdf (fallback).

Extracts text page-by-page, splits each page into indexed paragraphs, and
returns a list of DocumentChunk records. All processing happens in-memory;
the source bytes are never persisted to disk.
"""

from __future__ import annotations

import re
from typing import List

from app.schemas import DocumentChunk

# Imported lazily so the module imports cleanly even when optional deps are
# missing; callers surface a clear error at extraction time.


def _split_paragraphs(text: str) -> List[str]:
    """Split page text into paragraphs on blank-line boundaries."""
    # Normalize line endings and collapse excessive whitespace inside lines.
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    # Split on one or more blank lines.
    raw_paragraphs = re.split(r"\n\s*\n", normalized)
    paragraphs = []
    for para in raw_paragraphs:
        cleaned = " ".join(line.strip() for line in para.splitlines() if line.strip())
        if cleaned:
            paragraphs.append(cleaned)
    return paragraphs


def extract_pdf_chunks(file_bytes: bytes, filename: str) -> List[DocumentChunk]:
    """Extract indexed paragraph chunks from a PDF held entirely in memory.

    Strategy:
      1. Try pdfplumber (best layout/paragraph fidelity).
      2. Fall back to pypdf if pdfplumber fails or yields no text.
    """
    chunks: List[DocumentChunk] = []
    text_extracted = False

    # ---- Primary: pdfplumber -------------------------------------------
    try:
        import pdfplumber  # type: ignore
        import io

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page_index, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text() or ""
                if not page_text.strip():
                    continue
                text_extracted = True
                for para_index, para in enumerate(_split_paragraphs(page_text), start=1):
                    chunks.append(
                        DocumentChunk(
                            page_number=page_index,
                            paragraph_index=para_index,
                            raw_text=para,
                            confidence_score=0.96,  # digital PDF text is high confidence
                        )
                    )
    except Exception:  # pragma: no cover - fallback path
        text_extracted = False
        chunks = []

    # ---- Fallback: pypdf -----------------------------------------------
    if not text_extracted or not chunks:
        try:
            from pypdf import PdfReader  # type: ignore
            import io

            reader = PdfReader(io.BytesIO(file_bytes))
            chunks = []
            for page_index, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                if not page_text.strip():
                    continue
                text_extracted = True
                for para_index, para in enumerate(_split_paragraphs(page_text), start=1):
                    chunks.append(
                        DocumentChunk(
                            page_number=page_index,
                            paragraph_index=para_index,
                            raw_text=para,
                            confidence_score=0.92,
                        )
                    )
        except Exception as exc:  # pragma: no cover - hard dependency missing
            raise RuntimeError(
                "PDF extraction failed: neither pdfplumber nor pypdf could "
                f"read the document ({exc})"
            ) from exc

    if not chunks:
        raise ValueError("No extractable text found in the PDF (scanned/image-only PDF).")

    return chunks


def compose_document_text(chunks: List[DocumentChunk]) -> str:
    """Join chunks into a single document string with page/paragraph markers."""
    parts: List[str] = []
    for chunk in chunks:
        parts.append(
            f"[Page {chunk.page_number}, Para {chunk.paragraph_index}] {chunk.raw_text}"
        )
    return "\n\n".join(parts)
