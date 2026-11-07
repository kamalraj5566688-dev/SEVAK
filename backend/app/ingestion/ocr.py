"""Image OCR engine using OpenCV + pytesseract.

Preprocesses document photos (grayscale, denoising, adaptive thresholding) and
extracts structured text chunks. Includes a cheap document-presence check so
non-document photos (e.g. personal portraits) are not forced through OCR and
misclassified as notices. When Tesseract is unavailable or no usable text is
found, returns empty chunks with a fallback flag rather than fabricated text.
"""

from __future__ import annotations

import re
from typing import List, Tuple

from app.schemas import DocumentChunk

# Lazy imports so the module imports cleanly without system Tesseract present.


class OCRUnavailableError(RuntimeError):
    """Raised when Tesseract/OpenCV cannot perform OCR."""


def _looks_like_document(image) -> bool:
    """Cheap document-presence check using edge density and rectangular contour.

    Returns True when the image contains a dominant rectangular text region
    consistent with a scanned/photographed document. Personal photos with
    complex backgrounds and no dominant document contour return False.
    """
    import cv2  # type: ignore
    import numpy as np  # type: ignore

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    edge_density = float(np.count_nonzero(edges)) / float(edges.size)
    if edge_density < 0.02:
        return False

    contours, _ = cv2.findContours(
        edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    if not contours:
        return False

    largest = max(contours, key=cv2.contourArea)
    img_area = float(image.shape[0] * image.shape[1])
    if cv2.contourArea(largest) < img_area * 0.10:
        return False

    x, y, w, h = cv2.boundingRect(largest)
    aspect = w / h if h > 0 else 0.0
    if aspect < 0.30 or aspect > 3.00:
        return False
    return True


def _fallback_chunks() -> List[DocumentChunk]:
    """Empty chunk list used when OCR is unavailable or no text is found.

    No fabricated document text is returned; callers must treat an empty
    result as 'no readable content' rather than a real document.
    """
    return []


def _ocr_with_psm(thresh, pytesseract, psm: int) -> List[DocumentChunk]:
    """Run Tesseract with a given page-segmentation mode and return chunks."""
    data = pytesseract.image_to_data(
        thresh, config=f"--psm {psm}", output_type=pytesseract.Output.DICT
    )

    groups: dict[tuple, List[str]] = {}
    confidences: dict[tuple, List[float]] = {}
    n_boxes = len(data["text"])
    for i in range(n_boxes):
        word = (data["text"][i] or "").strip()
        if not word:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        groups.setdefault(key, []).append(word)
        try:
            confidences.setdefault(key, []).append(float(data["conf"][i]))
        except (ValueError, TypeError):
            confidences.setdefault(key, []).append(0.0)

    chunks: List[DocumentChunk] = []
    para_index = 0
    for key in sorted(groups.keys()):
        para_index += 1
        words = groups[key]
        if not words:
            continue
        line_text = " ".join(words)
        conf_list = confidences.get(key, [0.0])
        valid_conf = [c for c in conf_list if c >= 0]
        avg_conf = (sum(valid_conf) / len(valid_conf)) / 100.0 if valid_conf else 0.0
        avg_conf = max(0.0, min(1.0, avg_conf))

        if avg_conf < 0.10 and not _has_digit_or_alpha(line_text):
            continue

        chunks.append(
            DocumentChunk(
                page_number=1,
                paragraph_index=para_index,
                raw_text=line_text,
                confidence_score=round(avg_conf, 2),
            )
        )
    return chunks


def ocr_image_chunks(file_bytes: bytes, filename: str) -> Tuple[List[DocumentChunk], bool]:
    """Extract indexed paragraph chunks from an image document held in memory.

    Returns (chunks, is_fallback). is_fallback is True when Tesseract is
    unavailable, the image is not document-like, or no usable text was found.
    No fabricated document text is ever returned.
    """
    chunks: List[DocumentChunk] = []
    is_fallback = False

    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
        import pytesseract  # type: ignore

        nparr = np.frombuffer(file_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            raise OCRUnavailableError("Unable to decode image bytes.")

        # Document-presence gate: skip OCR for non-document photos.
        if not _looks_like_document(image):
            return [], True

        # Preprocessing: grayscale -> denoise -> adaptive threshold (primary)
        # for uneven photo lighting, Otsu as fallback.
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        thresh = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 31, 15,
        )

        # Try uniform-block PSM first; fall back to sparse text if too few words.
        chunks = _ocr_with_psm(thresh, pytesseract, 6)
        if len(chunks) < 3:
            chunks = _ocr_with_psm(thresh, pytesseract, 11)

    except (OCRUnavailableError, ImportError, Exception):
        is_fallback = True
        return [], True

    if not chunks:
        is_fallback = True
        return [], True

    return chunks, is_fallback


def _has_digit_or_alpha(text: str) -> bool:
    """True if text contains at least one letter or digit."""
    return bool(re.search(r"[A-Za-z0-9]", text))


def compose_document_text(chunks: List[DocumentChunk]) -> str:
    """Join OCR chunks into a single document string with markers."""
    parts: List[str] = []
    for chunk in chunks:
        parts.append(
            f"[Page {chunk.page_number}, Para {chunk.paragraph_index}] {chunk.raw_text}"
        )
    return "\n\n".join(parts)
