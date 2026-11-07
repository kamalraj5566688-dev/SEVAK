# Implementation Plan & Milestones: SEVAK

Execute tasks in strict sequential order. Do not jump to downstream milestones until the preceding validation gate passes.

---

## Phase 1: Environment & Client Adapters (Day 1)
- [ ] **Task 1.1: Project Scaffolding**
  - Initialize Next.js 14 App Router project with TypeScript and Tailwind CSS.
  - Setup FastAPI backend workspace with virtual environment.
- [ ] **Task 1.2: Gnani API Wrappers**
  - Write `backend/gnani/prisma.py` (STT adapter with mocked response fallback).
  - Write `backend/gnani/timbre.py` (TTS adapter with audio stream response).
- [ ] **Task 1.3: Verification Gate 1**
  - Execute a CLI test recording voice through Prisma and receiving audio back through Timbre.

---

## Phase 2: Ingestion & Evon 30B Core Engine (Day 2)
- [ ] **Task 2.1: Document Parser**
  - Implement `backend/ingestion/ocr.py` using `pypdf` and `pytesseract`.
  - Format output into indexed `DocumentChunk` records.
- [ ] **Task 2.2: Evon 30B Grounding Prompt**
  - Construct system prompt enforcing JSON schema, 3-action limits, and grounding references.
  - Connect endpoint to Hugging Face Inference API.
- [ ] **Task 2.3: Composite Gateway Endpoint**
  - Create `POST /api/analyze-notice` accepting multipart payload (document file + audio blob).
- [ ] **Task 2.4: Verification Gate 2**
  - Pass a sample 2-page banking notice and a recorded audio query; confirm valid JSON returns with page citations and synthesized audio.

---

## Phase 3: Frontend Interface & Player (Day 3 Morning)
- [ ] **Task 3.1: Voice Recording Component**
  - Build `components/AudioRecorder.tsx` with Web Audio API (16kHz WAV output).
  - Add press-to-speak mouse/touch handlers.
- [ ] **Task 3.2: WhatsApp-Style Chat Canvas**
  - Assemble chat messages, document previews, and severity badges.
- [ ] **Task 3.3: Timbre Voice Note Bubble**
  - Implement audio player with play/pause and progress scrubbing.
- [ ] **Task 3.4: "Show Me Where" Modal**
  - Build drawer/modal to view document text highlighted at the cited page/paragraph.
- [ ] **Task 3.5: Verification Gate 3**
  - Test end-to-end loop inside mobile browser emulator.

---

## Phase 4: Hardening, Demo Recording & Submission (Day 3 Afternoon & Evening)
- [ ] **Task 4.1: Edge Case & Safety Tuning**
  - Ensure documents with missing deadlines fall back gracefully to informational status.
  - Check that non-lawyer disclaimers appear on all views.
- [ ] **Task 4.2: Video Demo Recording (75 Seconds)**
  - Follow the 4-beat script: Notice Hook ➔ Prisma Input ➔ Timbre Output ➔ "Show Me Where" Proof.
- [ ] **Task 4.3: Social Campaign & Submission**
  - Push repository to GitHub with documentation.
  - Post demo on LinkedIn and X tagging `@Gnani AI` with `#GnaniAI` and `#GreatIndianAIInternshipChallenge`.
  - Complete the official Google Form before November 10, 2026.
