"""
Gemini API client wrapper.

Design decision
----------------
Every call goes through `generate_json`, which requests structured
JSON output directly from the model (`response_mime_type="application/json"`)
rather than asking for free text and hoping to parse it reliably.
Structured output mode is meaningfully more robust than prompt-only
JSON requests -- it's a real feature of the API, not just a
convention, and it dramatically reduces the "model added a stray
sentence before the JSON" class of parsing failure.

Errors (rate limits, network issues, malformed responses) are caught
here and re-raised as our own `LLMGenerationError` -- callers never
need to know whether a failure came from a 429, a timeout, or bad
JSON; they just need to know "this didn't work, degrade gracefully."
This mirrors the same pattern used for text extraction failures in
Milestone 4 and embedding failures in Milestone 6: an external
dependency failing should never crash the whole request.

Retry with backoff
-------------------
Transient failures (503 "high demand", 429 rate limit) are retried a
few times with short exponential backoff before giving up -- this was
added after hitting real 503s from Google's shared free-tier capacity
during Milestone 9 development. We deliberately do NOT retry on every
exception: a bad API key or a malformed prompt will fail the same way
every time, so retrying those just wastes time before the same
inevitable failure. Only errors whose message indicates a transient,
server-side condition are retried.
"""

import json
import time

from google import genai
from google.genai import types

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

_MAX_RETRIES = 3
_BASE_BACKOFF_SECONDS = 2
_TRANSIENT_ERROR_MARKERS = ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED")


class LLMGenerationError(Exception):
    """Raised when the LLM call fails or returns unusable output."""


def _get_client() -> genai.Client:
    if not settings.GEMINI_API_KEY:
        raise LLMGenerationError("GEMINI_API_KEY is not configured.")
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def _is_transient(exc: Exception) -> bool:
    message = str(exc)
    return any(marker in message for marker in _TRANSIENT_ERROR_MARKERS)


def generate_json(prompt: str, max_output_tokens: int = 500) -> dict:
    """
    Sends `prompt` to Gemini and returns the parsed JSON response.

    Retries up to `_MAX_RETRIES` times on transient errors (server
    overload, rate limiting) with exponential backoff (2s, 4s, 8s)
    before raising `LLMGenerationError`. Non-transient errors (bad API
    key, malformed request) fail immediately on the first attempt --
    no point waiting 14 seconds to learn the same thing a second time.
    """
    client = _get_client()
    last_exception: Exception | None = None

    for attempt in range(_MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    max_output_tokens=max_output_tokens,
                    temperature=0.4,
                ),
            )
            return json.loads(response.text)
        except json.JSONDecodeError as exc:
            # Not transient -- the model responded, just not with valid
            # JSON. Retrying the identical prompt is unlikely to help,
            # so fail immediately rather than burning retry budget.
            raise LLMGenerationError(f"Gemini returned non-JSON output: {exc}") from exc
        except Exception as exc:
            last_exception = exc
            if not _is_transient(exc) or attempt == _MAX_RETRIES - 1:
                logger.warning(f"Gemini API call failed (attempt {attempt + 1}/{_MAX_RETRIES}): {exc}")
                raise LLMGenerationError(f"Gemini API call failed: {exc}") from exc

            backoff = _BASE_BACKOFF_SECONDS * (2 ** attempt)
            logger.warning(
                f"Gemini API transient error (attempt {attempt + 1}/{_MAX_RETRIES}), "
                f"retrying in {backoff}s: {exc}"
            )
            time.sleep(backoff)

    # Unreachable in practice (the loop always returns or raises), but
    # keeps type checkers happy and fails loudly if that assumption
    # is ever violated.
    raise LLMGenerationError(f"Gemini API call failed after {_MAX_RETRIES} attempts: {last_exception}")
