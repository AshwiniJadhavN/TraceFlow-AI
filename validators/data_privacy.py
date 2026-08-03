"""Data minimization and leakage-prevention helpers.

These checks are intentionally conservative. They are not a substitute for an
enterprise DLP platform, but they prevent obvious sensitive identifiers from
being sent to an external model during prototype use.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class PrivacyScanResult:
    sanitized_text: str
    redactions: dict[str, int] = field(default_factory=dict)
    blocked_findings: list[str] = field(default_factory=list)

    @property
    def has_redactions(self) -> bool:
        return any(count > 0 for count in self.redactions.values())

    @property
    def is_blocked(self) -> bool:
        return bool(self.blocked_findings)


REDACTION_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "email",
        re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
        "[REDACTED_EMAIL]",
    ),
    (
        "phone",
        re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b"),
        "[REDACTED_PHONE]",
    ),
    (
        "patient_id",
        re.compile(
            r"\b(?:patient|subject|mrn|record)\s*(?:id|number|no\.?)?\s*[:#-]?\s*[A-Z0-9-]{5,}\b",
            re.IGNORECASE,
        ),
        "[REDACTED_PATIENT_ID]",
    ),
    (
        "api_key",
        re.compile(r"\b(?:sk-ant|sk-proj|sk)-[A-Za-z0-9_-]{12,}\b"),
        "[REDACTED_SECRET]",
    ),
]

BLOCK_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "possible_private_key",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"),
    ),
    (
        "possible_access_token",
        re.compile(
            r"\b(?:access_token|refresh_token|client_secret)\s*[:=]\s*['\"]?[A-Za-z0-9._~+/=-]{16,}",
            re.IGNORECASE,
        ),
    ),
]


def sanitize_for_model(text: str, *, block_sensitive: bool = True) -> PrivacyScanResult:
    """Return text with obvious sensitive identifiers redacted.

    If *block_sensitive* is true, high-risk secrets cause the scan to be marked
    as blocked so the caller can stop before any model call is made.
    """
    sanitized = text
    redactions: dict[str, int] = {}
    blocked_findings: list[str] = []

    for label, pattern, replacement in REDACTION_PATTERNS:
        sanitized, count = pattern.subn(replacement, sanitized)
        if count:
            redactions[label] = count

    if block_sensitive:
        for label, pattern in BLOCK_PATTERNS:
            if pattern.search(sanitized):
                blocked_findings.append(label)

    return PrivacyScanResult(
        sanitized_text=sanitized,
        redactions=redactions,
        blocked_findings=blocked_findings,
    )
