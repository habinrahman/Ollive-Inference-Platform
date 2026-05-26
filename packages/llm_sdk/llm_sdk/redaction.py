from __future__ import annotations

import re

EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")
SECRET_PATTERN = re.compile(
    r"\b(?:sk-[A-Za-z0-9_-]{12,}|[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,})\b"
)


def redact_text(value: str) -> str:
    redacted = EMAIL_PATTERN.sub("[redacted-email]", value)
    redacted = PHONE_PATTERN.sub("[redacted-phone]", redacted)
    return SECRET_PATTERN.sub("[redacted-secret]", redacted)
