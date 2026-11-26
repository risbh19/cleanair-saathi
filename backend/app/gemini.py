"""Small, bounded Google GenAI adapter. No automatic tool execution or retries."""
from collections import deque
from threading import Lock
from time import monotonic
import os
import re

from google import genai
from google.genai import types

_lock, _calls = Lock(), deque()


def provider_slot():
    with _lock:
        now = monotonic()
        while _calls and _calls[0] <= now - 60:
            _calls.popleft()
        if len(_calls) >= 12:
            return False
        _calls.append(now)
        return True


def enabled():
    return os.getenv("LLM_MODE", "reference") == "live" and bool(os.getenv("GEMINI_API_KEY"))


def model_name():
    model = os.getenv("GEMINI_MODEL") or "gemini-3.5-flash-lite"
    if not re.fullmatch(r"[a-zA-Z0-9.-]+", model):
        raise ValueError("Invalid Gemini model")
    return model


def generate(contents, *, system, schema=None, tools=None):
    if not enabled() or not provider_slot():
        return None
    # Function calling and structured outputs deliberately use separate requests.
    if schema is not None and tools is not None:
        raise ValueError("Separate tools and structured output")
    try:
        config = types.GenerateContentConfig(
            system_instruction=system, temperature=0, max_output_tokens=1200,
            response_mime_type="application/json" if schema is not None else None,
            response_schema=schema, tools=tools,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        with genai.Client(api_key=os.environ["GEMINI_API_KEY"],
                          http_options=types.HttpOptions(timeout=5000, retry_options=types.HttpRetryOptions(attempts=1))) as client:
            return client.models.generate_content(model=model_name(), contents=contents, config=config)
    except Exception:
        # SDK transport, quota, blocked responses and model errors share the offline path.
        # Do not log prompts, household data or provider exceptions containing credentials.
        return None
