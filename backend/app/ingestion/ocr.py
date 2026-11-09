"""Image OCR engine using OpenCV + pytesseract."""

from __future__ import annotations

import os
import re
from typing import List, Tuple

from app.schemas import DocumentChunk


class OCRUnavailableError(RuntimeError):
    """Raised when Tesseract/OpenCV cannot perform OCR."""


def _configure_tesseract(pytesseract):
    """Configure Windows Tesseract explicitly."""

    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]

    for path in candidates:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            return

    try:
        pytesseract.get_tesseract_version()
        return
    except Exception as exc:
        raise OCRUnavailableError(
            "Tesseract executable was not found."
        ) from exc


def _ocr_with_psm(
    image,
    pytesseract,
    psm: int,
    language: str = "hin+eng",
) -> List[DocumentChunk]:
    """Run Tesseract and convert detected text into document chunks."""

    data = pytesseract.image_to_data(
        image,
        lang=language,
        config=f"--psm {psm}",
        output_type=pytesseract.Output.DICT,
    )

    groups: dict[tuple, List[str]] = {}
    confidences: dict[tuple, List[float]] = {}

    for i in range(len(data["text"])):
        word = (data["text"][i] or "").strip()

        if not word:
            continue

        key = (
            data["block_num"][i],
            data["par_num"][i],
            data["line_num"][i],
        )

        groups.setdefault(key, []).append(word)

        try:
            confidence = float(data["conf"][i])
        except (ValueError, TypeError):
            confidence = 0.0

        confidences.setdefault(key, []).append(confidence)

    chunks: List[DocumentChunk] = []

    for key in sorted(groups.keys()):
        words = groups[key]

        if not words:
            continue

        line_text = " ".join(words).strip()

        if len(line_text) < 2:
            continue

        conf_list = confidences.get(key, [0.0])
        valid_conf = [c for c in conf_list if c >= 0]

        avg_conf = (
            (sum(valid_conf) / len(valid_conf)) / 100.0
            if valid_conf
            else 0.0
        )

        avg_conf = max(0.0, min(1.0, avg_conf))

        chunks.append(
            DocumentChunk(
                page_number=1,
                paragraph_index=len(chunks) + 1,
                raw_text=line_text,
                confidence_score=round(avg_conf, 2),
            )
        )

    return chunks


def ocr_image_chunks(
    file_bytes: bytes,
    filename: str,
) -> Tuple[List[DocumentChunk], bool]:
    """Extract OCR chunks from an image held in memory."""

    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
        import pytesseract  # type: ignore

        _configure_tesseract(pytesseract)

        nparr = np.frombuffer(file_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            raise OCRUnavailableError(
                "Unable to decode image bytes."
            )

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        height, width = gray.shape[:2]

        scale = 3.0 if max(height, width) < 1600 else 2.0

        resized = cv2.resize(
            gray,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC,
        )

        denoised = cv2.fastNlMeansDenoising(
            resized,
            None,
            10,
            7,
            21,
        )

        _, otsu = cv2.threshold(
            denoised,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU,
        )

        adaptive = cv2.adaptiveThreshold(
            denoised,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            11,
        )

        candidates = [
            denoised,
            otsu,
            adaptive,
        ]

        all_chunks: List[DocumentChunk] = []

        for candidate in candidates:
            for psm in (6, 11, 3):
                chunks = _ocr_with_psm(
                    candidate,
                    pytesseract,
                    psm,
                    language="hin+eng",
                )

                all_chunks.extend(chunks)

                if len(all_chunks) >= 8:
                    break

            if len(all_chunks) >= 8:
                break

        if not all_chunks:
            return [], True

        unique_chunks: List[DocumentChunk] = []
        seen: set[str] = set()

        for chunk in all_chunks:
            normalized = re.sub(
                r"\s+",
                " ",
                chunk.raw_text.strip().lower(),
            )

            if not normalized or normalized in seen:
                continue

            seen.add(normalized)

            unique_chunks.append(
                DocumentChunk(
                    page_number=1,
                    paragraph_index=len(unique_chunks) + 1,
                    raw_text=chunk.raw_text,
                    confidence_score=chunk.confidence_score,
                )
            )

        if not unique_chunks:
            return [], True

        return unique_chunks, False

    except (ImportError, OCRUnavailableError):
        return [], True

    except Exception:
        return [], True


def _has_digit_or_alpha(text: str) -> bool:
    """True if text contains at least one ASCII letter or digit."""
    return bool(re.search(r"[A-Za-z0-9]", text))


def compose_document_text(
    chunks: List[DocumentChunk],
) -> str:
    """Join OCR chunks into a single document string with markers."""

    parts: List[str] = []

    for chunk in chunks:
        parts.append(
            f"[Page {chunk.page_number}, Para "
            f"{chunk.paragraph_index}] {chunk.raw_text}"
        )

    return "\n\n".join(parts)
