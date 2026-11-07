"""Tests for the image OCR ingestion engine.

Tesseract is not installed in this environment, so these tests exercise the
graceful demo-fallback path and confirm OCR never crashes offline.
"""

from app.ingestion.ocr import ocr_image_chunks


def _make_png_bytes() -> bytes:
    """Minimal valid PNG (1x1 red pixel) as raw bytes."""
    import struct
    import zlib

    width, height = 1, 1
    raw = b"\x00" + bytes([255, 0, 0, 255]) * (width * height)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    ihdr = b"IHDR" + ihdr + struct.pack(">I", zlib.crc32(b"IHDR" + ihdr) & 0xFFFFFFFF)
    idat = zlib.compress(raw)
    idat = b"IDAT" + idat + struct.pack(">I", zlib.crc32(b"IDAT" + idat) & 0xFFFFFFFF)
    iend = b"IEND" + struct.pack(">I", zlib.crc32(b"IEND") & 0xFFFFFFFF)
    return b"\x89PNG\r\n\x1a\n" + ihdr + idat + iend


def test_ocr_returns_chunks_on_minimal_image():
    chunks, is_fallback = ocr_image_chunks(_make_png_bytes(), "test.png")
    assert isinstance(chunks, list)
    assert isinstance(is_fallback, bool)
    # Tesseract is not installed in this environment, so expect fallback.
    assert is_fallback is True
    assert len(chunks) == 0


def test_ocr_empty_bytes_falls_back_to_demo():
    chunks, is_fallback = ocr_image_chunks(b"", "empty.png")
    assert isinstance(chunks, list)
    assert is_fallback is True
    assert len(chunks) == 0
