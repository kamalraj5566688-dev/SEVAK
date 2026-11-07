# Data Contracts & Schemas: SEVAK

Because SEVAK runs an ephemeral, privacy-first pipeline, all data structures define memory payloads and API contracts rather than relational database tables.

---

## 1. Document Extraction Chunk Model (In-Memory)

```typescript
interface DocumentChunk {
  chunk_id: string;          // UUID v4
  page_number: number;       // 1-indexed
  paragraph_index: number;   // 1-indexed
  raw_text: string;          // OCR extracted text
  confidence_score: number;  // 0.0 - 1.0 (OCR confidence)
}
```

---

## 2. Gnani API Request & Response Contracts

### Prisma STT (Outbound Payload)
- **Method:** `POST`
- **Content-Type:** `multipart/form-data`
- **Fields:**
  - `audio`: Binary WAV file (16kHz, 16-bit, mono)
  - `lang`: `"hi-IN"` | `"bho-IN"` | `"auto"`

### Prisma STT (Inbound Response)
```json
{
  "status": "SUCCESS",
  "transcription": "Mera loan auto debit bounce ho gaya hai isme kitna penalty lagega?",
  "detected_language": "hi-IN",
  "confidence": 0.94
}
```

### Timbre TTS (Outbound Payload)
- **Method:** `POST`
- **Content-Type:** `application/json`
- **Payload:**
```json
{
  "text": "Yeh bank ka demand notice hai. Isme 15 din ke andar kul 14,250 rupaye jama karne ko kaha gaya hai.",
  "language": "hi-IN",
  "voice_gender": "Female",
  "audio_format": "wav"
}
```

---

## 3. SEVAK Core Reasoning Schema (Evon 30B Output Contract)

Evon 30B must return clean JSON validating against the following Pydantic schema:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SevakAnalysisResult",
  "type": "object",
  "properties": {
    "severity": {
      "type": "string",
      "enum": ["GREEN", "YELLOW", "RED"]
    },
    "severity_reason": {
      "type": "string",
      "description": "Short explanation for severity assignment"
    },
    "what": {
      "type": "string",
      "description": "Plain language definition of document type"
    },
    "why": {
      "type": "string",
      "description": "Cause or triggering event behind the notice"
    },
    "next_steps": {
      "type": "array",
      "items": { "type": "string" },
      "minItems": 3,
      "maxItems": 3,
      "description": "Exactly three practical actions for today"
    },
    "rights_and_protections": {
      "type": "string",
      "description": "Statutory rules or protections favoring the user"
    },
    "deadlines": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "action": { "type": "string" },
          "timeline": { "type": "string" },
          "source_page": { "type": "integer" }
        },
        "required": ["action", "timeline", "source_page"]
      }
    },
    "citations": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "claim": { "type": "string" },
          "source_location": { "type": "string" }
        },
        "required": ["claim", "source_location"]
      }
    },
    "spoken_summary_regional": {
      "type": "string",
      "description": "Natural spoken sentence in user language targeted for Timbre TTS synthesis"
    }
  },
  "required": [
    "severity",
    "severity_reason",
    "what",
    "why",
    "next_steps",
    "rights_and_protections",
    "citations",
    "spoken_summary_regional"
  ]
}
```
