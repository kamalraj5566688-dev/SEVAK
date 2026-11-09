from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

import httpx

from app.config import settings
from app.schemas import EvonAnalysisResult

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are SEVAK, an AI document assistant for Indian citizens.

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
"""


QA_SYSTEM_PROMPT = """You are SEVAK, a voice-first Indian document assistant.

You are NOT a lawyer.

Answer the user's question using the supplied document evidence only.

Rules:
- Do not invent facts.
- Do not make binding legal predictions.
- If evidence is missing, clearly say that the document does not establish it.
- Cite relevant evidence using Page X, Paragraph Y when possible.
- Keep the answer practical and conversational.
"""


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


class EvonReasoningClient:
    """Client for Gnani Evon reasoning model."""

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

    def get_target_url(self) -> Optional[str]:
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

    async def analyze(
        self,
        document_text: str,
        language: str = "hinglish",
    ) -> EvonAnalysisResult:

        target_url = self.get_target_url()

        if not self.api_token or not target_url:
            logger.info(
                "Evon credentials unavailable; using safe fallback."
            )
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

        hf_payload: dict[str, Any] = {
            "inputs": (
                SYSTEM_PROMPT
                + "\n\n"
                + user_prompt
            ),
            "parameters": {
                "temperature": 0.1,
                "max_new_tokens": 1200,
                "return_full_text": False,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    target_url,
                    headers=headers,
                    json=hf_payload,
                )

                if (
                    response.status_code in (400, 404, 422)
                    and "chat" not in target_url
                ):
                    chat_url = (
                        target_url.rstrip("/")
                        + "/v1/chat/completions"
                    )

                    chat_payload = {
                        "model": self.model_id or "evon-30b",
                        "messages": [
                            {
                                "role": "system",
                                "content": SYSTEM_PROMPT,
                            },
                            {
                                "role": "user",
                                "content": user_prompt,
                            },
                        ],
                        "temperature": 0.1,
                        "max_tokens": 1200,
                    }

                    chat_response = await client.post(
                        chat_url,
                        headers=headers,
                        json=chat_payload,
                    )

                    if chat_response.is_success:
                        raw = chat_response.json()
                        text = self._extract_chat_completion_text(raw)
                        data = self._parse_json(text)
                        return EvonAnalysisResult(**data)

                    response = chat_response

                if response.status_code == 503:
                    logger.warning(
                        "Evon model is loading (503)."
                    )
                    return EvonAnalysisResult(**DEMO_RESULT)

                response.raise_for_status()

                raw = response.json()

            text = self._extract_generated_text(raw)
            data = self._parse_json(text)

            return EvonAnalysisResult(**data)

        except Exception as exc:
            logger.error(
                "Evon inference failed: %s. Using safe fallback.",
                exc,
            )
            return EvonAnalysisResult(**DEMO_RESULT)

    async def ask(
        self,
        question: str,
        context: Optional[str] = None,
        language: str = "hinglish",
    ) -> str:

        target_url = self.get_target_url()

        if not self.api_token or not target_url:
            return self._demo_answer(question, language)

        prompt = (
            f"User language: {language}\n\n"
            f"User question: {question}\n\n"
        )

        if context:
            prompt += (
                "DOCUMENT EVIDENCE:\n"
                f"{context}\n\n"
            )
        else:
            prompt += (
                "No document evidence is available. "
                "Do not invent document-specific facts.\n\n"
            )

        prompt += (
            "Answer in 2-4 clear practical sentences. "
            "Use Page X, Paragraph Y citations when supported."
        )

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "inputs": QA_SYSTEM_PROMPT + "\n\n" + prompt,
            "parameters": {
                "temperature": 0.2,
                "max_new_tokens": 350,
                "return_full_text": False,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    target_url,
                    headers=headers,
                    json=payload,
                )

                if response.is_success:
                    raw = response.json()
                    answer = self._extract_generated_text(raw).strip()

                    if answer:
                        return answer

        except Exception as exc:
            logger.warning(
                "Evon QA failed: %s",
                exc,
            )

        return self._demo_answer(question, language)

    @staticmethod

    def _demo_answer(self, question: str, language: str = "Hinglish"):
        """Deterministic local fallback used when remote reasoning is unavailable.

        This fallback never pretends to be an LLM. It handles common conversational
        questions and gives an honest response for unsupported questions.
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
            "good evening"
        )

        identity_markers = (
            "who are you", "tum kaun ho", "aap kaun ho",
            "what are you", "what is sevak", "sevak kya hai",
            "sevak kaun hai"
        )

        capability_markers = (
            "what can you do", "kya kar sakte ho",
            "tum kya kar sakte ho", "aap kya kar sakte ho",
            "capabilities", "features", "help me"
        )

        thanks_markers = (
            "thanks", "thank you", "dhanyavad", "shukriya",
            "thankyou"
        )

        how_are_you_markers = (
            "how are you", "how r you", "kaise ho",
            "kaisa ho", "aap kaise hain", "tum kaise ho"
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
                "Main SEVAK hoon — Voice-First Indian Document Assistant. "
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

    def _extract_generated_text(raw: Any) -> str:

        if isinstance(raw, list) and raw:
            first = raw[0]

            if isinstance(first, dict):
                for key in (
                    "generated_text",
                    "text",
                    "response",
                ):
                    if isinstance(first.get(key), str):
                        return first[key]

        if isinstance(raw, dict):
            for key in (
                "generated_text",
                "text",
                "response",
            ):
                if isinstance(raw.get(key), str):
                    return raw[key]

        return str(raw)

    @staticmethod
    def _extract_chat_completion_text(raw: Any) -> str:

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

        cleaned = text.strip()

        cleaned = re.sub(
            r"^```(?:json)?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

        cleaned = re.sub(
            r"\s*```$",
            "",
            cleaned,
        )

        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if start != -1 and end > start:
            cleaned = cleaned[start:end + 1]

        try:
            return json.loads(cleaned)

        except json.JSONDecodeError:

            return {
                "severity": "YELLOW",
                "severity_reason": (
                    "The reasoning model did not return valid structured data."
                ),
                "what": (
                    "SEVAK could not safely interpret the document."
                ),
                "why": (
                    "The AI response could not be validated."
                ),
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
