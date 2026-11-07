# Tech Stack Specifications: SEVAK

Every package and engine in SEVAK is constrained below. Do not swap libraries or introduce unsupported cloud dependencies.

---

## 1. Frontend Framework & Runtime
- **Framework:** Next.js 14.2+ (App Router)
- **Language:** TypeScript 5.4+
- **Styling:** Tailwind CSS 3.4+
- **Icons:** `lucide-react` (v0.380+)
- **Audio Capture:** Native Web Audio API / `MediaRecorder` (`audio/wav`, linear PCM 16kHz mono)
- **Audio Playback:** Native HTML5 `<audio>` element with custom controls

---

## 2. Backend API & Engine
- **Framework:** FastAPI 0.111+ (Python 3.11+)
- **Server:** Uvicorn (ASGI)
- **Validation:** Pydantic v2.7+
- **PDF Extraction:** `pypdf` 4.2+ & `pdfplumber` 0.11+
- **Image OCR:** `pytesseract` 0.3.10+ with OpenCV (`opencv-python-headless` 4.9+)
- **HTTP Client:** `httpx` 0.27+ (asynchronous requests for external APIs)

---

## 3. AI Models & Voice Services
- **Speech-to-Text (STT):** Gnani **Prisma** API
  - Endpoint: `https://api.gnani.ai/v1/stt`
  - Encoding: WAV / 16000 Hz / Mono
  - Target Locales: `hi-IN`, `bho-IN`, and code-mixed auto-detect
- **Text-to-Speech (TTS):** Gnani **Timbre** API
  - Endpoint: `https://api.gnani.ai/v1/tts`
  - Voice Engines: Hindi / Bhojpuri female/male standard neural voices
  - Output Format: WAV / MP3 streaming
- **Reasoning LLM:** Gnani **Evon 30B** (via Hugging Face Dedicated Inference Endpoint)
  - Decoding: `temperature=0.1`, `max_tokens=1024`, enforced JSON output mode

---

## 4. Environment & Deployment Constraints
- **Client Deployment:** Vercel
- **Backend Deployment:** Render or Railway (Linux x86_64 with Tesseract binary installed)
- **Environment Variables Required:**
  - `GNANI_API_KEY`: 5,000 credit developer token
  - `GNANI_PRISMA_ENDPOINT`: Target STT URI
  - `GNANI_TIMBRE_ENDPOINT`: Target TTS URI
  - `HF_TOKEN`: Hugging Face auth token for Evon 30B
  - `NEXT_PUBLIC_BACKEND_URL`: FastAPI host URL
