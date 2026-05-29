"""PIIScrubber — best-effort masking for logs.

Patterns intentionally minimal; real deployments should plug in a proper
PII detector (regex pack + ML).
"""
from __future__ import annotations

import re

_PHONE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
_ID = re.compile(r"\b\d{15}|\d{18}\b")


def scrub(text: str) -> str:
    if not text:
        return text
    text = _PHONE.sub("***[phone]***", text)
    text = _EMAIL.sub("***[email]***", text)
    text = _ID.sub("***[id]***", text)
    return text
