# PR: feat(evon): Few-Shot Indic Legal Examples + 4 bug fixes

## Summary

Hardens the Gnani Evon-30B reasoning client (`backend/app/gnani/evon.py`) and stabilizes its integration with the API layer (`backend/app/api/routes.py`). The change injects few-shot Indic legal examples into the system prompt, fixes four defects (two decorator mismatches, Unicode encoding corruption, and the `ask()` return-type inconsistency), and switches both `analyze()` and `ask()` to the OpenAI-compatible `/v1/chat/completions` endpoint as the primary API path.

## Bug Fixes

| # | Bug | Fix | File |
| --- | --- | --- | --- |
| 1 | `_demo_answer` declared with `self` but no `@staticmethod`, so `self._demo_answer(question, language)` passed the client instance as `question` and produced garbage answers. | Added `@staticmethod` and corrected the signature to `_demo_answer(question, language="Hinglish")`. | `backend/app/gnani/evon.py:528` |
| 2 | `_extract_generated_text` was called as `self._extract_generated_text(...)` without `@staticmethod`, same class of `self`-binding bug. | Added `@staticmethod`. (Now unused by the active code path but kept correct for any future text-generation fallback.) | `backend/app/gnani/evon.py:619` |
| 3 | Hinglish strings contained literal Unicode (e.g. the em-dash `—`) vulnerable to encoding corruption/mojibake across toolchains. | Replaced the literal with the escaped form `\u2014`; all Indic text remains native UTF-8. | `backend/app/gnani/evon.py:587` |
| 4 | `ask()` returned a `dict` (the raw `_demo_answer` payload or an extracted text dict), while `routes.py` consumed it as a plain `str` (passed to `_clean_grounded_text()` and TTS). A dict was silently stringified into `"{'status': ...}"`, breaking voice output and downstream string methods. | `ask()` now returns `str` in every path — the live chat completion content, or `self._demo_answer(...)["answer"]` on failure. All `routes.py` callers (`_answer_from_evon`, `/api/ask`, `/api/voice-query`) already treat the result as a string, so no caller changes were required. | `backend/app/gnani/evon.py:450-521` |

## Core Upgrade: Few-Shot Indic Legal Prompting

- Added `FEW_SHOT_EXAMPLES` covering three high-frequency Indian legal document classes:
  1. Income Tax Notice — Section 148 reassessment (severity RED)
  2. Rent Eviction / Rent Recovery Notice under the Maharashtra Rent Control Act, 1999 (severity YELLOW — pre-litigation, no court order yet)
  3. Bank Loan Default Notice — SARFAESI Act Section 13(2) (severity RED — property seizure risk)
- Each example models the exact output schema: `document_type`, `severity`/`severity_reason`, Hinglish `what`/`why`, exactly 3 `next_steps`, `rights_and_protections` with a "not a lawyer" disclaimer, `deadlines`, `citations` in `Page X, Paragraph Y` form, and a one-sentence `spoken_summary_regional`.
- The examples are prepended to `SYSTEM_PROMPT`, teaching Evon-30B the output format, Indian legal tone, citation discipline, and severity calibration with zero fine-tuning and no GPU.
- `QA_SYSTEM_PROMPT` gained an explicit instruction to match Hindi/Hinglish/English to the user's language.

Expected impact:

- Reasoning: structured evidence → conclusion chain reduces format drift and preamble noise.
- Citation accuracy: repeated `Page X, Paragraph Y` examples reinforce the grounding rules; server-side `validate_citations()` (grounding.py) still strips any citation pointing to non-existent page/paragraph labels.
- Severity calibration: explicit GREEN/YELLOW/RED definitions plus worked examples anchor RED on statutory deadlines/penalty/property-seizure risk and YELLOW on pre-litigation notices. Watch item: the strong example priors may over-escalate generic tax/bank documents to RED; monitor in production.

## Architectural Improvements

- `/v1/chat/completions` (OpenAI-compatible) is now the primary API path for both `analyze()` and `ask()`, replacing the raw-text `inputs` format (HF text-generation-inference style) that proved unreliable on the Hugging Face Inference Router.
- New `get_chat_url()` helper appends `/v1/chat/completions` to the base URL resolved by `get_target_url()` (supports either a dedicated endpoint URL or a model ID routed through `https://router.huggingface.co/hf-inference/models/<id>`).
- Both methods now build a unified `messages: [system, user]` payload and extract answers via `_extract_chat_completion_text()` (`choices[0].message.content`), standardizing the chat format across the client.
- 503 (model loading) and general request failures degrade to the safe `DEMO_RESULT` / local demo fallback instead of crashing.

Note: the module docstring states that `ask()` retries on 400/404/422. The current implementation does not implement an explicit retry — it uses `/v1/chat/completions` as the primary path and falls back to the demo answer on failure or empty response. Either implement the retry or correct the docstring before merge.

## Verification

- Backend test suite: `pytest backend/tests/` — 13 passed.
- Also fixed a pre-existing import gap uncovered during validation: `routes.py` used `CitationItem` in `_local_document_analysis()` but never imported it (`NameError` when Evon falls back to local analysis). Added `CitationItem` to the imports in `backend/app/api/routes.py`. All tests now pass.
