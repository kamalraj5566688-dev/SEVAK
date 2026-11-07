# Product Requirements Document (PRD): SEVAK
**Project Name:** SEVAK (Smart Explanation & Voice-Assisted Kanoon)  
**Hackathon:** Great Indian AI Internship Challenge (Gnani AI)  
**Submission Deadline:** November 10, 2026  
**Primary Focus:** Low-latency voice-in/voice-out Indic legal & civic notice interpretation.

---

## 1. Executive Summary
SEVAK is a voice-first web application designed for non-English speakers and semi-literate citizens across Bharat who receive official, legal, banking, or municipal notices. Users photograph or upload an official document and speak questions naturally in code-mixed Indic languages (Hindi, Hinglish, Bhojpuri). SEVAK transcribes the query, cross-references grounded sections of the document, evaluates statutory urgency, and speaks an actionable explanation back to the user.

---

## 2. Target Audience & Personas
1. **Ramesh (Gig Economy / Delivery Worker, Patna):** Receives a complex English bank notice regarding loan auto-debits; cannot parse formal clauses and risks aggressive recovery agent harassment.
2. **Sunita (Small Kirana Store Owner):** Receives a municipal tax demand; needs to know the exact deadline and payment channel without paying an intermediary.

---

## 3. Core MVP Feature Scope (In-Scope)
- **F-01: Document Extraction:** OCR and chunking for PDFs and mobile photos (`.pdf`, `.png`, `.jpg`).
- **F-02: Voice Input (Gnani Prisma STT):** Captures 16kHz mono audio queries in Hindi, Hinglish, and regional dialects.
- **F-03: Grounded Reasoning (Evon 30B LLM):** Enforces a 4-part framework:
  - **WHAT:** Document nature and issuing entity.
  - **WHY:** Triggering cause/event.
  - **NEXT:** Exactly 3 immediate, practical actions.
  - **RIGHTS:** Applicable protections (e.g., RBI Fair Practice guidelines).
- **F-04: Document Severity Indicator:** Explicit classification based on detected statutory terms:
  - 🟢 **GREEN (Informational):** Policy updates, generic releases.
  - 🟡 **YELLOW (Action Required):** KYC renewals, fee deadlines > 30 days.
  - 🔴 **RED (Urgent):** Court summons, Section 138 notices, deadlines < 15 days.
- **F-05: Voice Output (Gnani Timbre TTS):** Regional spoken synthesis of the executive summary and 3 action items.
- **F-06: "Show Me Where" Grounding:** Strict mapping of every core claim to an indexed page and paragraph.
- **F-07: Statutory Legal Safety Shield:** Non-lawyer disclaimer injection; rejection of predictive legal guarantees.

---

## 4. Out-of-Scope (Strict Exclusions for MVP)
- **NO User Accounts / Authentication:** No email signups, phone OTPs, or session databases. The MVP operates entirely on ephemeral session IDs.
- **NO Direct WhatsApp Bot Integration:** Pure web application designed with a WhatsApp-style UI. Do not install the Meta Graph API or Twilio.
- **NO E-Filing / Government Portal Automation:** SEVAK does not submit forms or initiate legal filings on behalf of the user.
- **NO Fine-Tuning Pipelines:** Use Evon 30B and Gnani models via prompt engineering and parameter tuning only.
- **NO Long-Term Storage of Raw Personal Documents:** Uploaded files and audio payloads must expire and delete after analysis.
