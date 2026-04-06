"""Groq LLM wrapper with rate limiting for all use cases."""
import time
import json
from groq import Groq
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))
from config import GROQ_API_KEY, GROQ_MODEL, GROQ_RPM_LIMIT

_client = None
_last_call_time = 0
_min_interval = 60.0 / GROQ_RPM_LIMIT  # seconds between calls


def get_client():
    global _client
    if _client is None:
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


def rate_limit():
    global _last_call_time
    elapsed = time.time() - _last_call_time
    if elapsed < _min_interval:
        time.sleep(_min_interval - elapsed)
    _last_call_time = time.time()


def call_llm(prompt, system_prompt="You are a helpful assistant.", temperature=0.1, max_tokens=1024):
    """Call Groq Llama 3 70B with rate limiting. Returns the response text."""
    rate_limit()
    try:
        client = get_client()
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"  LLM call failed: {e}")
        return None


def call_llm_json(prompt, system_prompt="You are a helpful assistant. Always respond with valid JSON only.", temperature=0.1, max_tokens=1024):
    """Call LLM and parse response as JSON. Returns dict or None."""
    text = call_llm(prompt, system_prompt=system_prompt, temperature=temperature, max_tokens=max_tokens)
    if text is None:
        return None
    # Strip markdown code fences if present
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print(f"  Failed to parse JSON: {text[:200]}")
        return None
