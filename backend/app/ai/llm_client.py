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
"""

import json

from google import genai
from google.genai import types

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class LLMGenerationError(Exception):
    """Raised when the LLM call fails or returns unusable output."""


def _get_client() -> genai.Client:
    if not settings.GEMINI_API_KEY:
        raise LLMGenerationError("GEMINI_API_KEY is not configured.")
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def generate_json(prompt: str, max_output_tokens: int = 500) -> dict:
    """
    Sends `prompt` to Gemini and returns the parsed JSON response.

    Raises `LLMGenerationError` on any failure -- rate limit, network
    issue, or a response that isn't valid JSON despite the structured
    output request. Never raises Gemini's own exception types directly,
    so callers only need to handle one error type regardless of cause.
    """
    try:
        client = _get_client()
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
        raise LLMGenerationError(f"Gemini returned non-JSON output: {exc}") from exc
    except Exception as exc:
        # Deliberately broad: the Gemini SDK can raise several different
        # exception types (rate limit, auth, network, quota) and we want
        # every one of them to degrade the same way for our callers.
        logger.warning(f"Gemini API call failed: {exc}")
        raise LLMGenerationError(f"Gemini API call failed: {exc}") from exc
