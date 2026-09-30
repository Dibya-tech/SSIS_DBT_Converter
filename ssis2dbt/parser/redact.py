"""Credential redaction, applied at the parser layer (PRD section 10.3).

Sensitive values never enter the IR, models, logs, or reports.
"""
from __future__ import annotations

import re

REDACTED = "***REDACTED***"

# Keys whose values must be masked whole.
_SENSITIVE_KEYS = re.compile(
    r"(password|pwd|token|accountkey|sharedaccesssignature|secret|credential)",
    re.IGNORECASE,
)

# Connection-string fragments to strip: key=value pairs with sensitive keys.
_CONN_PAIR = re.compile(
    r"(password|pwd|account\s*key|shared\s*access\s*signature|token)\s*=\s*[^;]*",
    re.IGNORECASE,
)


def is_sensitive_key(key: str) -> bool:
    return bool(_SENSITIVE_KEYS.search(key or ""))


def redact_value(value: str) -> str:
    if value is None:
        return value
    return _CONN_PAIR.sub(lambda m: f"{m.group(1)}={REDACTED}", value)


def redact_properties(props: dict) -> dict:
    """Return a copy of props with sensitive values redacted."""
    out = {}
    for k, v in (props or {}).items():
        if is_sensitive_key(k):
            out[k] = REDACTED
        elif isinstance(v, str):
            out[k] = redact_value(v)
        else:
            out[k] = v
    return out
