# Implementation Plan & Milestones: SEVAK

Execute tasks in strict sequential order. Do not jump to downstream milestones until the preceding validation gate passes.

---

## Phase 1: Environment & Client Adapters (Day 1)
- [x] **Task 1.1: Project Scaffolding**
  - Initialize Vite + React 19 project with TypeScript and Tailwind CSS.
  - Setup FastAPI backend workspace with virtual environment.
- [x] **Task 1.2: Gnani API Wrappers**
  - Write `backend/app/gnani/prisma.py` (STT adapter with Indic dialect cleanup and fallback).
  - Write `backend/app/gnani/timbre.py` (TTS adapter with live audio stream response).
- [x] **Task 1.3: Verification Gate 1**
  - Execute a CLI test recording voice through Prisma and receiving audio back through Timbre (verified live in `backend/verify_apis.py`).

---

## Phase 2: Ingestion & Evon 30B Core Engine (Day 2)
- [x] **Task 2.1: Document Parser**
  - Implement `backend/app/ingestion/ocr.py` using `pypdf`, `pdfplumber`, and `pytesseract`.
  - Format output into indexed `DocumentChunk` records.
- [x] **Task 2.2: Evon 30B Grounding Prompt**
  - Construct system prompt enforcing JSON schema, exactly 3 next steps, and grounded citations.
  - Connect client to Hugging Face model (`gnani/gnani-evon-v3.3-30B-A3B`) with fallback to local reasoning engine.
- [x] **Task 2.3: Composite Gateway Endpoint**
  - Create `POST /api/analyze-document` accepting multipart payload (document file + language).
- [x] **Task 2.4: Verification Gate 2**
  - Pass sample banking notice and traffic challan; confirm valid JSON returns with page citations and synthesized audio.

---

## Phase 3: Frontend Interface & Player (Day 3 Morning)
- [x] **Task 3.1: Voice Recording Component**
  - Build `src/components/VoiceModal.tsx` with Web Audio / Speech API (16kHz WAV output).
  - Add press-to-speak and interactive modal handlers.
- [x] **Task 3.2: WhatsApp-Style Chat Canvas**
  - Assemble chat messages, document previews, and severity badges.
- [x] **Task 3.3: Timbre Voice Note Bubble**
  - Implement audio player with play/pause and progress scrubbing in `src/components/ResultsView.tsx`.
- [x] **Task 3.4: "Show Me Where" Grounding Section**
  - Build UI section mapping each core claim to indexed page and paragraph numbers.
- [x] **Task 3.5: Verification Gate 3**
  - Test end-to-end loop inside browser emulator with Vite.

---

## Phase 4: Hardening, Demo Recording & Submission (Day 3 Afternoon & Evening)
- [x] **Task 4.1: Edge Case & Safety Tuning**
  - Ensure documents with missing deadlines fall back gracefully to informational status.
  - Check that non-lawyer statutory safety shield disclaimers appear on all views.
- [ ] **Task 4.2: Video Demo Recording (75 Seconds)**
  - Follow the 5-beat script: Notice Hook ➔ Prisma Input ➔ Timbre Output ➔ "Show Me Where" Proof ➔ Call to Action.
- [ ] **Task 4.3: Social Campaign & Submission**
  - Push repository to GitHub with complete documentation. *(Completed)*
  - Post demo on LinkedIn and X tagging `@Gnani AI` with `#GnaniAI` and `#GreatIndianAIInternshipChallenge`.
  - Complete the official Google Form before November 10, 2026.
