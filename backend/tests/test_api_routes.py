"""End-to-end API route tests using FastAPI's TestClient.

Covers /health and /api/analyze-document with an in-memory PDF, plus the
voice endpoints. All external Gnani/Hugging Face calls fall back to demo
responses since no API keys are configured in the test environment.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _make_text_pdf_bytes() -> bytes:
    """Build a minimal valid PDF with extractable Latin text (Helvetica base font)."""
    text = (
        "DEMO OFFICIAL NOTICE. Payment is due within 15 days from the date of issue. "
        "Contact the issuing authority for clarification."
    )
    esc = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content = f"BT /F1 12 Tf 72 720 Td ({esc}) Tj ET".encode("latin-1")

    obj1 = b"<< /Type /Catalog /Pages 2 0 R >>"
    obj2 = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
    obj3 = (
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
    )
    obj4 = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    obj5 = b"<< /Length %d >>stream\n%s\nendstream" % (len(content), content)

    objects = [None, obj1, obj2, obj3, obj4, obj5]
    offsets = []
    out = bytearray()
    out += b"%PDF-1.4\n"
    for i in range(1, 6):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode()
        out += objects[i]
        out += b"\nendobj\n"
    xref_offset = len(out)
    out += b"xref\n"
    out += f"0 {len(objects)}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += b"trailer\n<< /Size 6 /Root 1 0 R >>\n"
    out += b"startxref\n"
    out += f"{xref_offset}\n".encode()
    out += b"%%EOF\n"
    return bytes(out)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "SEVAK Backend"
    assert data["version"] == "1.0.0"


def test_analyze_document_with_pdf():
    pdf_bytes = _make_text_pdf_bytes()
    response = client.post(
        "/api/analyze-document",
        files={"document": ("notice.pdf", pdf_bytes, "application/pdf")},
        data={"language": "hinglish"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["id"]
    assert data["document_title"]
    assert data["category"] in {
        "Traffic Police Notice",
        "Banking & KYC",
        "Income Tax Department",
        "Government Notice",
        "Legal Summons",
        "Unrecognized / Not a Document",
    }
    assert data["original_file_name"] == "notice.pdf"
    assert data["file_type"] == "application/pdf"
    assert 0.0 <= data["confidence_score"] <= 1.0
    assert 0.0 <= data["classification_confidence"] <= 1.0
    # Frontend shape checks
    assert data["what"]["summary"]
    assert data["what"]["details"]
    assert data["why"]["significance"]
    assert data["why"]["urgency_reason"]
    assert len(data["next_steps"]) == 3
    assert all(s["step"] for s in data["next_steps"])
    assert data["rights"]["title"]
    assert isinstance(data["rights"]["safeguards"], list)
    assert "SEVAK is an AI document-assistant" in data["rights"]["disclaimer"]
    assert isinstance(data["deadline"]["has_deadline"], bool)
    assert data["source"]["issuing_authority"]
    assert data["source"]["legal_section"]
    assert data["source"]["reference_number"]
    # Voice summaries for all supported languages
    for lang in ("hinglish", "hindi", "english", "bhojpuri", "maithili"):
        assert lang in data["voice_summaries"]
        assert data["voice_summaries"][lang]


def test_analyze_document_rejects_unsupported_type():
    response = client.post(
        "/api/analyze-document",
        files={"document": ("notice.exe", b"MZ\x90\x00", "application/octet-stream")},
        data={"language": "hinglish"},
    )
    assert response.status_code == 415


def test_transcribe_audio_fallback():
    response = client.post(
        "/api/voice/transcribe",
        files={"audio": ("query.wav", b"RIFF....WAVE", "audio/wav")},
        data={"language": "hi-IN"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "transcript" in data


def test_ask_question_endpoint():
    response = client.post(
        "/api/ask",
        json={"question": "What is the deadline?", "language": "hinglish"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data and data["answer"]


def test_voice_query_alias_endpoint():
    response = client.post(
        "/api/voice-query",
        json={"question": "Kya mujhe court jana hoga?", "language": "hindi"},
    )
    assert response.status_code == 200
    assert "answer" in response.json()


def test_tts_endpoint():
    response = client.post(
        "/api/tts",
        json={"text": "Namaste! Main SEVAK hoon.", "language": "hi-IN"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["audio_base64"]
    assert data["audio_format"] == "wav"
    assert "duration_seconds" in data
