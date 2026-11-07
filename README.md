# SEVAK — Voice-First Indian Document Assistant

> **Samjhega. Batayega. Raasta dikhayega.**

SEVAK is a voice-first Indian document assistant designed to make confusing notices, bank and loan letters, government documents, and other important communications easier to understand.

Instead of providing only a generic summary, SEVAK is designed to explain a document through:

**WHAT → WHY → NEXT STEPS → RIGHTS → DEADLINE → SOURCE**

The goal is simple: help users understand important documents in simple language and identify what they should do next.

---

## 🚀 Key Features

- 📄 Upload documents and images
- 🎙️ Ask questions using your own voice
- 🧠 AI-powered document understanding
- 🗣️ Voice-based responses
- 🌐 Hindi, Hinglish, and regional-language support
- 🔎 Extract important information from documents
- ⏰ Identify important dates and deadlines
- ✅ Generate practical next steps
- ⚖️ Explain relevant rights and responsibilities mentioned in the source
- 📌 Show the source/evidence behind important information
- 💬 Ask follow-up questions about the same document
- 🛡️ Safety-focused responses with uncertainty handling
- 📱 Responsive desktop and mobile interface

---

## 🎯 The Problem

Important Indian documents can be difficult to understand because they often contain:

- Complex terminology
- Formal or legal language
- Long paragraphs
- Important deadlines hidden inside the document
- Instructions that are difficult for non-technical users to interpret
- Multiple pieces of information spread across different sections

For many users, the real problem is not receiving the document — it is understanding **what it means and what to do next**.

SEVAK aims to bridge this gap by converting complicated documents into simple, structured, and actionable explanations.

---

## 💡 How SEVAK Helps

### WHAT

What does this document actually say?

### WHY

Why did the user receive it and why does it matter?

### NEXT

What are the most important actions the user should consider taking next?

### RIGHTS

What rights, responsibilities, options, or protections are explicitly mentioned in the document?

### DEADLINE

Are there important dates or deadlines that the user should notice?

### SOURCE

Where did the information come from?

SEVAK is designed to keep the explanation connected to the original document rather than producing an unsupported generic answer.

---

## 🧠 AI Architecture

SEVAK follows a voice-first AI workflow.

```text
                         USER
                           │
              ┌────────────┴────────────┐
              │                         │
         DOCUMENT                   VOICE
       PDF / IMAGE                 QUESTION
              │                         │
              └────────────┬────────────┘
                           ▼
                    SEVAK FRONTEND
                           │
                           ▼
                      BACKEND API
                           │
              ┌─────────────┼─────────────┐
              │             │             │
              ▼             ▼             ▼
           PRISMA         EVON          TIMBRE
        Speech-to-Text   Reasoning    Text-to-Speech
              │             │             │
              └─────────────┼─────────────┘
                            ▼
                     SEVAK RESPONSE
                            │
              ┌─────────────┴─────────────┐
              │                           │
           TEXT ANSWER                VOICE ANSWER
```

---

## 🎙️ Gnani AI Integration

SEVAK is being developed for the **Great Indian AI Internship Challenge** and is designed to genuinely use Gnani AI's voice and AI capabilities.

### Prisma

Used for speech-to-text and voice input processing.

### Evon

Used for reasoning, document understanding, and generating structured responses.

### Timbre

Used for text-to-speech and voice responses.

Sensitive API credentials are intended to remain on the backend rather than being exposed in frontend source code.

---

## 🛠️ Technology Stack

### Frontend

- React
- TypeScript
- Vite
- CSS
- Responsive UI

### AI / Voice

- Gnani AI
- Prisma
- Evon
- Timbre

### Backend

The backend is responsible for:

- Document upload
- Document processing
- AI API communication
- Voice processing
- Secure API key handling
- Frontend/backend integration
- Error handling
- Deployment

---

## 📂 Project Structure

```text
SEVAK/
│
├── public/
│   └── assets/
│
├── src/
│   ├── components/
│   │   ├── ActionButtons.tsx
│   │   ├── AnalyzingView.tsx
│   │   ├── Footer.tsx
│   │   ├── Hero.tsx
│   │   ├── HowSevakHelps.tsx
│   │   ├── LanguageSelector.tsx
│   │   ├── Navbar.tsx
│   │   ├── ResultsView.tsx
│   │   ├── RobotIllustration.tsx
│   │   ├── SafetyCard.tsx
│   │   ├── UploadModal.tsx
│   │   └── VoiceModal.tsx
│   │
│   ├── data/
│   │   └── sampleDocuments.ts
│   │
│   ├── services/
│   │   └── api.ts
│   │
│   ├── types/
│   │   └── index.ts
│   │
│   ├── App.tsx
│   ├── index.css
│   └── main.tsx
│
├── index.html
├── package.json
├── package-lock.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

---

## ⚙️ Run Locally

### Prerequisites

Make sure you have:

- Node.js
- npm
- Git

### 1. Clone the repository

```bash
git clone https://github.com/kamalraj5566688-dev/SEVAK.git
cd SEVAK
```

### 2. Install dependencies

```bash
npm install
```

### 3. Configure environment variables

Create the required environment configuration using `.env.example` as a reference.

Do not commit API keys, passwords, tokens, or other secrets to GitHub.

### 4. Start the development server

```bash
npm run dev
```

### 5. Build for production

```bash
npm run build
```

---

## 🔐 Security

SEVAK follows a backend-first approach for sensitive API credentials.

API keys should not be placed directly inside frontend source code.

The intended architecture is:

```text
Frontend
   │
   ▼
Backend API
   │
   ▼
Gnani AI APIs
```

This helps keep sensitive credentials on the server side.

---

## ⚖️ Responsible AI & Safety

SEVAK is an **information and document-explanation assistant**.

It is **not a lawyer, legal authority, financial advisor, or government authority**.

SEVAK should not:

- Guarantee legal outcomes
- Predict the result of a legal case
- Claim that a user will definitely win or lose
- Invent information that is not supported by the document
- Present uncertain information as fact
- Replace qualified professional advice

When a situation requires professional assistance, SEVAK should clearly communicate its limitations and encourage the user to seek appropriate professional help.

---

## 🌍 Designed for India

SEVAK is designed with India's diverse language and accessibility needs in mind.

The project is intended to support:

- English
- Hindi
- Hinglish
- Bhojpuri
- Maithili
- Additional Indian languages in future versions

The long-term goal is to make important information accessible through natural voice interaction instead of relying only on complicated written language.

---

## 🏆 Great Indian AI Internship Challenge

SEVAK is being developed as a project for the:

**Great Indian AI Internship Challenge by Gnani AI**

The project focuses on:

- Voice-first AI
- Indian languages
- Real-world document understanding
- Accessibility
- Responsible AI
- Practical AI applications
- Gnani AI voice and reasoning capabilities

---

## 👥 Team

### AI/ML Lead & Frontend

**Divyanshu Raj**

Responsibilities:

- AI/ML workflow design
- Voice AI integration
- AI prompt and reasoning design
- Multilingual behavior
- Document understanding logic
- Frontend architecture
- UI/UX implementation
- Testing

### Backend Lead

**Kamal**

Responsibilities:

- Backend API
- Document processing
- Gnani API integration
- Secure credential handling
- Frontend/backend integration
- Deployment and backend infrastructure

---

## 📊 Development Status

| Component | Status |
|---|---|
| Frontend UI | ✅ Completed |
| Responsive Design | ✅ Completed |
| Document Upload UI | ✅ Completed |
| Voice Interaction UI | ✅ Completed |
| Analysis UI | ✅ Completed |
| Results UI | ✅ Completed |
| Backend Integration | 🚧 In Progress |
| Gnani Prisma Integration | 🚧 In Progress |
| Gnani Evon Integration | 🚧 In Progress |
| Gnani Timbre Integration | 🚧 In Progress |
| End-to-End Testing | 🚧 In Progress |
| Final Challenge Submission | 🚧 In Progress |

---

## 🔮 Future Scope

Planned improvements include:

- WhatsApp-based document assistance
- More Indian regional languages
- Improved OCR for scanned documents
- Official-source verification
- Better evidence extraction
- Document comparison
- Voice conversation history
- Improved accessibility
- Government scheme discovery
- Personalized action guidance
- Better multilingual voice interaction

---

## 🤝 Contribution

SEVAK is currently being developed as a team project.

For major changes, discuss the proposed change with the project team before making significant modifications to the shared repository.

---

## 📄 License & Copyright

This project is licensed under the [MIT License](LICENSE).

```text
Copyright (c) 2026 SEVAK Team (kamalraj5566688-dev & Contributors)
All Rights Reserved. Developed for the Great Indian AI Internship Challenge (Gnani AI).
```

---

## ❤️ SEVAK

> **Samjhega. Batayega. Raasta dikhayega.**

Making important Indian documents easier to understand — one voice conversation at a time.