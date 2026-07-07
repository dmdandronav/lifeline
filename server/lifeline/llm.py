"""Optional LLM enhancement layer.

Everything in LIFELINE works offline; this module only activates when an
``ANTHROPIC_API_KEY`` is present *and* the ``anthropic`` package is installed
(``pip install -e ".[llm]"``). It rewrites the stall agent's canned replies so
consecutive calls feel less scripted. Any failure — missing key, missing
package, API error — falls back to the deterministic reply.
"""

from __future__ import annotations

import os

DEFAULT_MODEL = "claude-opus-4-8"
_MAX_REPLY_TOKENS = 300

_client = None  # lazily constructed anthropic.Anthropic


def llm_available() -> bool:
    """True when the optional LLM layer can be used."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def _get_client():
    global _client
    if _client is None:
        import anthropic

        _client = anthropic.Anthropic()
    return _client


def enhance_stall_reply(scammer_text: str, canned_reply: str) -> str:
    """Rewrite a canned stall reply with an LLM, falling back on any failure.

    The persona and time-wasting intent of the canned reply must be preserved;
    the LLM only varies the surface phrasing so repeated demos don't sound
    identical. Deterministic behaviour (and the tests) never depend on this.
    """
    if not llm_available():
        return canned_reply
    try:
        client = _get_client()
        response = client.messages.create(
            model=os.environ.get("LIFELINE_LLM_MODEL", DEFAULT_MODEL),
            max_tokens=_MAX_REPLY_TOKENS,
            system=(
                "You rewrite one line of dialogue for 'Margaret', a sweet, "
                "rambling grandmother persona used by a DEFENSIVE anti-scam "
                "demo to waste a phone scammer's time. Keep the same stalling "
                "intent and rough length. Never reveal real information, never "
                "agree to pay, never break character. Reply with the rewritten "
                "line only."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Scammer said: {scammer_text!r}\n"
                        f"Current canned reply: {canned_reply!r}\n"
                        "Rewrite the reply."
                    ),
                }
            ],
        )
        if response.stop_reason == "refusal":
            return canned_reply
        text = next((b.text for b in response.content if b.type == "text"), "")
        return text.strip() or canned_reply
    except Exception:
        # The demo must never break because of the optional layer.
        return canned_reply
