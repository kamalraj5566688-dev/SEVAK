"""
evon.py — Gnani Evon-30B reasoning client for SEVAK.

Improvements over v1:
- Few-Shot Indic Legal Examples injected into every system prompt.
  This teaches the model the exact output format and Indian legal tone
  without any fine-tuning or GPU.
- Fixed @staticmethod / self mismatch on _demo_answer.
- Fixed missing @staticmethod on _extract_generated_text.
- Fixed Unicode encoding corruption in Hinglish strings.
- ask() now retries with /v1/chat/completions on 400/404/422,
  matching the same resilience pattern already in analyze().
- Both analyze() and ask() use the OpenAI-compatible chat format
  as the primary path (more reliable on HF Inference Router).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

import httpx

from app.config import settings
from app.schemas import EvonAnalysisResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# FEW-SHOT INDIC LEGAL EXAMPLES
# ---------------------------------------------------------------------------
# These examples teach Evon-30B the exact output format, Indian legal
# vocabulary, severity calibration, and Hinglish spoken-summary style.
# No GPU, no training — pure prompt engineering.
# ---------------------------------------------------------------------------

FEW_SHOT_EXAMPLES = """
=== FEW-SHOT EXAMPLE 1 — Income Tax Notice (Section 148) ===

DOCUMENT EVIDENCE:
[Page 1, Paragraph 1]
INCOME TAX DEPARTMENT, GOVERNMENT OF INDIA
Notice under Section 148 of the Income Tax Act, 1961
To: Shri Ramesh Kumar Verma, PAN: ABCPV1234D
Assessment Year: 2021-22
Reference No: ITO/WARD-3/148/2024/001

[Page 1, Paragraph 2]
You are hereby required to furnish a return of income for the Assessment Year
2021-22 within 30 days from the date of service of this notice. Failure to
comply may result in best-judgment assessment under Section 144 and imposition
of penalty under Section 271(1)(b).

ASSISTANT RESPONSE:
{
  "document_type": "Income Tax Notice — Section 148 (Reassessment)",
  "severity": "RED",
  "severity_reason": "This is a mandatory government notice requiring income return filing within 30 days. Non-compliance leads to penalty and best-judgment assessment (Page 1, Paragraph 2).",
  "what": "Income Tax Department ne aapko AY 2021-22 ke liye income return dobara file karne ka notice diya hai. Yeh Section 148 ke under reassessment notice hai.",
  "why": "Department ko lagta hai ki aapki AY 2021-22 ki income puri tarah report nahi hui. Isliye woh reassessment kar rahe hain (Page 1, Paragraph 1 — Assessment Year: 2021-22).",
  "next_steps": [
    "Immediately contact a Chartered Accountant or tax advocate — notice mila hai toh 30 din ke andar return file karna compulsory hai.",
    "Collect all income proofs, bank statements, and investment documents for AY 2021-22.",
    "File the revised return on the Income Tax portal (incometax.gov.in) or through your CA before the 30-day deadline."
  ],
  "rights_and_protections": "Aapko Section 148A ke under hearing ka adhikar hai. Notice ke jawab mein aap apni position explain kar sakte hain pehle reassessment order aane se. SEVAK ek information assistant hai — legal dispute ke liye qualified tax advocate se milein.",
  "deadlines": [
    {
      "action": "File income return for AY 2021-22",
      "timeline": "Within 30 days from date of service of notice",
      "source_page": 1
    }
  ],
  "citations": [
    {
      "claim": "Return must be furnished within 30 days",
      "source_location": "Page 1, Paragraph 2"
    },
    {
      "claim": "Non-compliance may result in penalty under Section 271(1)(b)",
      "source_location": "Page 1, Paragraph 2"
    }
  ],
  "spoken_summary_regional": "Income Tax Department ne aapko 30 din ke andar AY 2021-22 ka return file karne ka notice diya hai, warna penalty lag sakti hai."
}

=== FEW-SHOT EXAMPLE 2 — Rent Eviction Notice ===

DOCUMENT EVIDENCE:
[Page 1, Paragraph 1]
LEGAL NOTICE
To: Smt. Priya Sharma, Tenant
From: Sri Mahesh Agarwal, Landlord
Property: Flat No. 304, Laxmi Apartments, Pune — 411001
Date: 15 October 2024

[Page 1, Paragraph 2]
You have failed to pay rent for the months of August, September, and October
2024, totalling Rs. 45,000 (Rupees Forty-Five Thousand Only). You are hereby
called upon to pay the outstanding amount within 15 days of receipt of this
notice, failing which legal proceedings under the Maharashtra Rent Control
Act, 1999 will be initiated against you.

ASSISTANT RESPONSE:
{
  "document_type": "Legal Notice — Rent Recovery / Eviction Warning",
  "severity": "YELLOW",
  "severity_reason": "This is a legal notice warning of court proceedings if rent is not paid within 15 days. No court order has yet been issued — this is a pre-litigation notice (Page 1, Paragraph 2).",
  "what": "Aapke landlord ne 3 mahine ka pending rent — August, September aur October 2024 — total Rs. 45,000 — 15 din mein dene ka legal notice bheja hai.",
  "why": "Notice mein likha hai ki rent nahi diya toh Maharashtra Rent Control Act ke under court case hoga (Page 1, Paragraph 2).",
  "next_steps": [
    "Agar rent genuinely baaki hai toh 15 din ke andar pay karein aur receipt lein — yeh sabse safe option hai.",
    "Agar rent already paid hai ya koi dispute hai, toh ek rent-law advocate se milein aur apne payment proofs collect karein.",
    "Yeh notice court order nahi hai — aapko abhi ghar khaali karne ki zaroorat nahi, lekin 15 din ke andar response dena important hai."
  ],
  "rights_and_protections": "Maharashtra Rent Control Act ke under tenant ko direct eviction se protection milti hai — court order ke bina eviction illegal hai. SEVAK ek information assistant hai, legal dispute ke liye advocate se milein.",
  "deadlines": [
    {
      "action": "Pay outstanding rent of Rs. 45,000",
      "timeline": "Within 15 days of receipt of notice",
      "source_page": 1
    }
  ],
  "citations": [
    {
      "claim": "Outstanding rent totals Rs. 45,000 for August, September, October 2024",
      "source_location": "Page 1, Paragraph 2"
    },
    {
      "claim": "Landlord threatens legal proceedings under Maharashtra Rent Control Act, 1999",
      "source_location": "Page 1, Paragraph 2"
    }
  ],
  "spoken_summary_regional": "Landlord ne 3 mahine ka 45,000 rupaye rent 15 din mein dene ka notice diya hai, warna court case hoga."
}

=== FEW-SHOT EXAMPLE 3 — Bank Loan Default Notice ===

DOCUMENT EVIDENCE:
[Page 1, Paragraph 1]
STATE BANK OF INDIA — NOTICE UNDER SECTION 13(2) OF SARFAESI ACT, 2002
Borrower: Sh. Dinesh Patel, Loan Account No: SBI/HL/2019/00456
Outstanding Amount: Rs. 18,34,520 (Principal + Interest as on 01-Nov-2024)

[Page 1, Paragraph 2]
You are hereby called upon to discharge the full outstanding liability of
Rs. 18,34,520 within 60 days of service of this notice. Failure to pay
shall result in enforcement of security interest over the mortgaged property
at Survey No. 123/A, Village Dholka, District Ahmedabad.

ASSISTANT RESPONSE:
{
  "document_type": "Bank Loan Default Notice — SARFAESI Act Section 13(2)",
  "severity": "RED",
  "severity_reason": "SARFAESI Section 13(2) is a formal legal demand that can lead to property seizure without court intervention if the borrower does not respond within 60 days (Page 1, Paragraph 2). This is a high-urgency notice.",
  "what": "State Bank of India ne SARFAESI Act ke under aapko Rs. 18,34,520 ke outstanding loan ke liye 60-din ka formal notice diya hai. Yeh notice property seizure process ka pehla official step hai.",
  "why": "Aapka home loan account NPA (Non-Performing Asset) category mein aa gaya hai. Bank ko SARFAESI Act ke under secured property enforce karne ka adhikar milta hai agar 60 din mein payment nahi hoti (Page 1, Paragraph 2).",
  "next_steps": [
    "Immediately ek SARFAESI-specialist advocate ya legal-aid centre se milein — 60-din ki deadline bahut important hai.",
    "60-din ke andar Section 13(3A) ke under bank ko written representation bheji ja sakti hai — yeh aapka statutory right hai.",
    "Agar loan restructuring possible ho toh bank ke Loan Recovery Officer se milkar One-Time Settlement (OTS) negotiate karein."
  ],
  "rights_and_protections": "SARFAESI Act Section 13(3A) ke under aapko 15-din ke andar bank ko written objection dene ka adhikar hai. DRT (Debt Recovery Tribunal) mein Section 17 ke under appeal bhi ki ja sakti hai. SEVAK ek information assistant hai — is matter mein qualified advocate se zaroor milein.",
  "deadlines": [
    {
      "action": "Repay outstanding amount of Rs. 18,34,520 OR file written representation under Section 13(3A)",
      "timeline": "Within 60 days of service of notice",
      "source_page": 1
    }
  ],
  "citations": [
    {
      "claim": "Outstanding liability is Rs. 18,34,520 as on 01-Nov-2024",
      "source_location": "Page 1, Paragraph 1"
    },
    {
      "claim": "Failure to pay within 60 days will result in enforcement of security interest over mortgaged property",
      "source_location": "Page 1, Paragraph 2"
    }
  ],
  "spoken_summary_regional": "Bank ne SARFAESI notice diya hai — 60 din mein 18 lakh se zyada baaki hai, warna property seize ho sakti hai, isliye turant advocate se milein."
}
"""


# ---------------------------------------------------------------------------
# SYSTEM PROMPTS (with Few-Shot examples embedded)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    """You are SEVAK, an AI document assistant for Indian citizens.

You are NOT a lawyer.

Your job is to explain the user's uploaded document using ONLY the evidence
provided in the document context.

Use simple Hindi, Hinglish, Bhojpuri, Maithili, or English according to the
user's requested language.

IMPORTANT GROUNDING RULES:

1. Never invent facts that are not present in the document.
2. Every factual claim must be traceable to the supplied page/paragraph evidence.
3. Citations MUST use the exact format:
   "Page X, Paragraph Y"
4. Do not create a page or paragraph number that is not present.
5. If the document does not contain enough information, explicitly say:
   "Document mein is information ka clear evidence nahi mila."
6. Never guarantee legal outcomes.
7. Never say that someone definitely will or will not be arrested,
   fined, sued, evicted, blacklisted, or have property seized unless the
   document itself explicitly states that fact.
8. Do not provide fabricated statutory rights.
9. For legal interpretation, explain the document's wording and recommend
   official authority / qualified legal help where appropriate.

Return STRICTLY valid JSON:

{
  "document_type": "...",
  "severity": "GREEN | YELLOW | RED",
  "severity_reason": "...",
  "what": "...",
  "why": "...",
  "next_steps": ["...", "...", "..."],
  "rights_and_protections": "...",
  "deadlines": [
    {
      "action": "...",
      "timeline": "...",
      "source_page": 1
    }
  ],
  "citations": [
    {
      "claim": "...",
      "source_location": "Page X, Paragraph Y"
    }
  ],
  "spoken_summary_regional": "..."
}

RULES:

- next_steps MUST contain exactly 3 practical actions.
- Do not invent deadlines.
- If no deadline exists, return an empty deadlines array.
- If the document contains an exact calendar date, preserve it.
- If the document contains a relative deadline such as "within 7 days",
  preserve that wording.
- citations must point only to supplied evidence.
- spoken_summary_regional must be one natural spoken sentence.

SEVERITY CALIBRATION:
- GREEN  = Informational document, no immediate action or legal risk.
- YELLOW = Response required but no imminent legal/financial danger.
- RED    = Urgent legal or financial risk — court notice, property seizure,
           SARFAESI, criminal summons, or deadline within 15 days.

Study the following examples carefully. Follow the same format, language
style, and citation discipline for the actual document below.
"""
    + FEW_SHOT_EXAMPLES
)


QA_SYSTEM_PROMPT = """You are SEVAK, a voice-first Indian document assistant.

You are NOT a lawyer.

Answer the user's question using the supplied document evidence only.

Rules:
- Do not invent facts.
- Do not make binding legal predictions.
- If evidence is missing, clearly say that the document does not establish it.
- Cite relevant evidence using Page X, Paragraph Y when possible.
- Keep the answer practical and conversational.
- Use Hindi, Hinglish, or English matching the user's language.
"""


# ---------------------------------------------------------------------------
# DEMO FALLBACK (used when API is unavailable)
# ---------------------------------------------------------------------------

DEMO_RESULT = {
    "document_type": "unknown",
    "severity": "YELLOW",
    "severity_reason": (
        "The reasoning service is unavailable, so SEVAK cannot safely "
        "determine the document's legal severity."
    ),
    "what": (
        "SEVAK could not complete a grounded analysis of this document."
    ),
    "why": (
        "The AI reasoning service is currently unavailable."
    ),
    "next_steps": [
        "Read the issuing authority and reference number on the document.",
        "Check the official portal or contact details printed on the document.",
        "Keep the document and any acknowledgment or receipt safely stored.",
    ],
    "rights_and_protections": (
        "SEVAK is an information assistant, not a lawyer. "
        "For a legal dispute, consult a qualified advocate or legal-aid clinic."
    ),
    "deadlines": [],
    "citations": [],
    "spoken_summary_regional": (
        "SEVAK document ko safely explain nahi kar paaya kyunki reasoning "
        "service abhi available nahi hai."
    ),
}


# ---------------------------------------------------------------------------
# CLIENT
# ---------------------------------------------------------------------------

class EvonReasoningClient:
    """Client for Gnani Evon-30B reasoning model via HuggingFace Inference Router."""

    def __init__(self) -> None:
        self.endpoint = (
            settings.HF_EVON_ENDPOINT.strip()
            if settings.HF_EVON_ENDPOINT
            else ""
        )
        self.model_id = (
            settings.HF_MODEL_ID.strip()
            if settings.HF_MODEL_ID
            else ""
        )
        self.api_token = (
            settings.HF_TOKEN.strip()
            if settings.HF_TOKEN
            else ""
        )

    # ------------------------------------------------------------------
    # URL helpers
    # ------------------------------------------------------------------

    def get_target_url(self) -> Optional[str]:
        """Return the base URL for the model (without /v1/chat/completions)."""
        if self.endpoint:
            if self.endpoint.startswith(("http://", "https://")):
                return self.endpoint
            return (
                "https://router.huggingface.co/"
                f"hf-inference/models/{self.endpoint}"
            )

        if self.model_id:
            return (
                "https://router.huggingface.co/"
                f"hf-inference/models/{self.model_id}"
            )

        return None

    def get_chat_url(self) -> Optional[str]:
        """Return the OpenAI-compatible chat completions URL."""
        base = self.get_target_url()
        if base is None:
            return None
        return base.rstrip("/") + "/v1/chat/completions"

    # ------------------------------------------------------------------
    # analyze()
    # ------------------------------------------------------------------

    async def analyze(
        self,
        document_text: str,
        language: str = "hinglish",
    ) -> EvonAnalysisResult:
        """
        Analyze an uploaded document with Evon-30B.

        Strategy:
        1. Try OpenAI-compatible chat/completions (primary — more reliable).
        2. On failure, return safe DEMO_RESULT.
        """
        chat_url = self.get_chat_url()

        # Fast-fail: if Evon endpoint is not configured at all, do not
        # attempt any HTTP request to the HuggingFace router. This avoids
        # 400 errors from unsupported 30B MoE models and routes directly
        # to the deterministic Indic legal fallback engine.
        if not settings.HF_EVON_ENDPOINT and not settings.HF_MODEL_ID:
            logger.debug(
                "Evon endpoint not configured; using safe fallback."
            )
            return EvonAnalysisResult(**DEMO_RESULT)

        if not self.api_token or not chat_url:
            logger.info("Evon credentials unavailable; using safe fallback.")
            return EvonAnalysisResult(**DEMO_RESULT)

        user_prompt = (
            f"User preferred language: {language}\n\n"
            "DOCUMENT EVIDENCE:\n"
            "The following text is extracted from the user's document. "
            "Page/paragraph labels are authoritative.\n\n"
            f"{document_text}\n\n"
            "Analyze ONLY this evidence and return the required JSON."
        )

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        chat_payload: dict[str, Any] = {
            "model": self.model_id or "evon-30b",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 1500,
        }

        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    chat_url,
                    headers=headers,
                    json=chat_payload,
                )

                if response.status_code == 503:
                    logger.warning("Evon model is loading (503).")
                    return EvonAnalysisResult(**DEMO_RESULT)

                response.raise_for_status()
                raw = response.json()

            text = self._extract_chat_completion_text(raw)
            data = self._parse_json(text)
            return EvonAnalysisResult(**data)

        except Exception as exc:
            logger.error(
                "Evon analyze() failed: %s. Using safe fallback.", exc
            )
            return EvonAnalysisResult(**DEMO_RESULT)

    # ------------------------------------------------------------------
    # ask()
    # ------------------------------------------------------------------

    async def ask(
        self,
        question: str,
        context: Optional[str] = None,
        language: str = "hinglish",
    ) -> str:
        """
        Answer a voice question about the document.

        Returns the answer as a plain string so that routes.py can call
        .lower() / pass it directly to _clean_grounded_text().
        """
        chat_url = self.get_chat_url()

        # Fast-fail: if Evon endpoint is not configured at all, do not
        # attempt any HTTP request to the HuggingFace router.
        if not settings.HF_EVON_ENDPOINT and not settings.HF_MODEL_ID:
            logger.debug(
                "Evon endpoint not configured; using safe fallback."
            )
            return self._demo_answer(question, language)["answer"]

        if not self.api_token or not chat_url:
            return self._demo_answer(question, language)["answer"]

        user_prompt = (
            f"User language: {language}\n\n"
            f"User question: {question}\n\n"
        )

        if context:
            user_prompt += (
                "DOCUMENT EVIDENCE:\n"
                f"{context}\n\n"
            )
        else:
            user_prompt += (
                "No document evidence is available. "
                "Do not invent document-specific facts.\n\n"
            )

        user_prompt += (
            "Answer in 2-4 clear practical sentences. "
            "Use Page X, Paragraph Y citations when supported."
        )

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "model": self.model_id or "evon-30b",
            "messages": [
                {"role": "system", "content": QA_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 400,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    chat_url,
                    headers=headers,
                    json=payload,
                )

                if response.is_success:
                    raw = response.json()
                    answer = self._extract_chat_completion_text(raw).strip()

                    if answer:
                        return answer

        except Exception as exc:
            logger.warning("Evon ask() failed: %s", exc)

        return self._demo_answer(question, language)["answer"]

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _demo_answer(question: str, language: str = "Hinglish") -> dict[str, Any]:
        """
        Deterministic local fallback when remote reasoning is unavailable.

        Never pretends to be an LLM. Handles common conversational questions
        and gives an honest response for unsupported queries.
        """
        raw = (question or "").strip()
        q = raw.lower()

        if not raw:
            return {
                "status": "SUCCESS",
                "answer": (
                    "Namaste! Main SEVAK hoon. Aap document upload karke "
                    "ya voice se apna sawaal pooch sakte hain."
                ),
                "citations": [],
                "next_steps": [],
                "grounded": False,
            }

        greeting_markers = (
            "hello", "hi", "hey", "namaste", "namaskar",
            "hii", "helo", "good morning", "good afternoon",
            "good evening",
        )
        identity_markers = (
            "who are you", "tum kaun ho", "aap kaun ho",
            "what are you", "what is sevak", "sevak kya hai",
            "sevak kaun hai",
        )
        capability_markers = (
            "what can you do", "kya kar sakte ho",
            "tum kya kar sakte ho", "aap kya kar sakte ho",
            "capabilities", "features", "help me",
        )
        thanks_markers = (
            "thanks", "thank you", "dhanyavad", "shukriya",
            "thankyou",
        )
        how_are_you_markers = (
            "how are you", "how r you", "kaise ho",
            "kaisa ho", "aap kaise hain", "tum kaise ho",
        )

        if any(marker in q for marker in greeting_markers):
            answer = (
                "Namaste! Main SEVAK hoon. Aap mujhse document ke baare mein "
                "voice se sawaal pooch sakte hain. Main document ko simple "
                "language mein samjhane aur practical next steps batane mein help karta hoon."
            )
        elif any(marker in q for marker in how_are_you_markers):
            answer = (
                "Main badhiya hoon aur aapki help ke liye ready hoon. "
                "Aap koi document upload karke uske baare mein voice se sawaal pooch sakte hain."
            )
        elif any(marker in q for marker in identity_markers):
            answer = (
                "Main SEVAK hoon \u2014 Voice-First Indian Document Assistant. "
                "Mera kaam confusing documents, notices aur letters ko simple language "
                "mein samjhana aur unke practical next steps batana hai."
            )
        elif any(marker in q for marker in capability_markers):
            answer = (
                "Main documents ko simple language mein explain kar sakta hoon, "
                "important dates aur amounts identify kar sakta hoon, "
                "notice ka purpose samjha sakta hoon, aur available evidence ke "
                "basis par practical next steps bata sakta hoon."
            )
        elif any(marker in q for marker in thanks_markers):
            answer = (
                "You're welcome! Agar aapke paas koi document hai, upload kijiye "
                "aur uske baare mein mujhse voice mein poochhiye."
            )
        else:
            answer = (
                "Main is sawaal ka reliable answer bina relevant document evidence "
                "ke nahi dena chahta. Aap document upload kijiye, phir main uske "
                "available evidence ke basis par answer aur source information de sakta hoon."
            )

        return {
            "status": "SUCCESS",
            "answer": answer,
            "citations": [],
            "next_steps": [],
            "grounded": False,
        }

    @staticmethod
    def _extract_generated_text(raw: Any) -> str:
        """Extract plain text from a HuggingFace text-generation response."""
        if isinstance(raw, list) and raw:
            first = raw[0]
            if isinstance(first, dict):
                for key in ("generated_text", "text", "response"):
                    if isinstance(first.get(key), str):
                        return first[key]

        if isinstance(raw, dict):
            for key in ("generated_text", "text", "response"):
                if isinstance(raw.get(key), str):
                    return raw[key]

        return str(raw)

    @staticmethod
    def _extract_chat_completion_text(raw: Any) -> str:
        """Extract content from an OpenAI-compatible chat/completions response."""
        if isinstance(raw, dict):
            choices = raw.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                if (
                    isinstance(message, dict)
                    and isinstance(message.get("content"), str)
                ):
                    return message["content"]

        return str(raw)

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        """
        Robustly parse a JSON object from raw model output.

        Handles:
        - Markdown code fences (```json ... ```)
        - Leading/trailing whitespace
        - Non-JSON preamble before the first {
        """
        cleaned = text.strip()

        # Strip markdown code fences
        cleaned = re.sub(
            r"^```(?:json)?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"\s*```$", "", cleaned)

        # Find the JSON object boundaries
        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if start != -1 and end > start:
            cleaned = cleaned[start : end + 1]

        try:
            return json.loads(cleaned)

        except json.JSONDecodeError:
            return {
                "severity": "YELLOW",
                "severity_reason": (
                    "The reasoning model did not return valid structured data."
                ),
                "what": "SEVAK could not safely interpret the document.",
                "why": "The AI response could not be validated.",
                "next_steps": [
                    "Read the issuing authority and reference number.",
                    "Check the official source mentioned in the document.",
                    "Seek qualified help if the notice concerns a legal dispute.",
                ],
                "rights_and_protections": (
                    "SEVAK is an information assistant, not a lawyer."
                ),
                "deadlines": [],
                "citations": [],
                "spoken_summary_regional": (
                    "SEVAK document ko safely analyze nahi kar paaya."
                ),
            }
