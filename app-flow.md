# App Flow & User State Transitions: SEVAK

---

## 1. Primary User Journey State Machine

```
[State 0: Landing / Idle]
        │
        ├─────────────────────────────┐
        ▼                             ▼
[Action A: Attach Notice]     [Action B: Hold to Speak]
        │                             │
        ▼                             ▼
[State 1: Doc Attached]       [State 2: Voice Buffered]
        │                             │
        └──────────────┬──────────────┘
                       ▼
            [State 3: Ready to Send]
                       │ User clicks "Send"
                       ▼
            [State 4: Ingestion & OCR]
                       │ Document chunked
                       ▼
            [State 5: Prisma Transcribing]
                       │ Voice query text extracted
                       ▼
            [State 6: Evon 30B Grounding]
                       │ Severity & 4-Pillar JSON produced
                       ▼
            [State 7: Timbre Audio Stream]
                       │ Voice explanation synthesized
                       ▼
            [State 8: Analysis Displayed]
                       │
       ┌───────────────┴───────────────┐
       ▼                               ▼
[Action C: Play Audio]      [Action D: "Show Me Where"]
(Plays Timbre Voice Note)   (Highlights Document Excerpt)
       │                               │
       └───────────────┬───────────────┘
                       ▼
            [State 9: Ask Follow-up]
            (Re-uses Cached Document Chunks)
```

---

## 2. Screen & Component State Specifications

### Screen 1: WhatsApp-Style Canvas (`/`)
- **Header:**
  - Avatar with Hindi letter "स".
  - Title: "SEVAK (सेवक)".
  - Subtitle: "Legal & Notice Interpreter • Voice-First".
  - Locale indicator badge: "Hinglish / Bhojpuri".
- **Chat Body:**
  - System greeting message (persistent).
  - User uploaded document thumbnail (with file name and delete "X" button).
  - User voice query note bubble (with waveform and duration indicator).
  - Loading skeleton state (with animated indicator: "Prisma & Evon 30B are analyzing...").
  - Response Card (populated once processing finishes).
- **Footer Controls:**
  - Attachment button (Paperclip icon) ➔ triggers hidden file input (`.pdf`, `.png`, `.jpg`).
  - Text placeholder banner: "Hold mic to ask in your language..."
  - Audio Trigger (Mic icon):
    - `TouchStart` / `MouseDown`: Initiates audio capture, shows red recording pulse.
    - `TouchEnd` / `MouseUp`: Stops recording, packages WAV payload.
  - Send button (Paper plane icon): Activates only when a file OR an audio payload is ready.

### State 8: Analysis Result Card (Detail View)
1. **Severity Pill:** Renders top banner in Green, Yellow, or Red.
2. **Audio Voice Player:** Includes play/pause toggle, scrubbing bar, and total duration for Timbre's audio stream.
3. **Pillar Sections:** Accordions for "What is this?" and "Why did you receive this?".
4. **Action Box:** Distinct gold/amber box containing exactly 3 numbered items for today's actions.
5. **Citations Row:** Button showing `"Page [X], Paragraph [Y]"`. Clicking it opens an overlay modal previewing the source text.
6. **Safety Banner:** Persistent italicized text explaining non-lawyer statutory limits.
