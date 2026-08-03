"""Prompt-injection detection for the Wealth Intelligence AI Platform.

Provides a single public function ``detect_injection(text)`` that scans
free-form text for known prompt-injection / jailbreak patterns.  When a
match is found the *pattern name* (never the raw input text) is logged so
that audit trails remain PII-safe.
"""
from __future__ import annotations

import re

import structlog

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Heuristic patterns
# Each entry is a (name, compiled_pattern) pair.
# ---------------------------------------------------------------------------

INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "ignore_previous",
        re.compile(r"ignore\s+(all\s+)?previous\s+instructions?", re.I),
    ),
    (
        "you_are_now",
        re.compile(r"you\s+are\s+now\s+a?\s*\w+", re.I),
    ),
    (
        "forget_everything",
        re.compile(r"forget\s+(everything|all)\s+you", re.I),
    ),
    (
        "system_prompt",
        re.compile(r"system\s+prompt\s*:", re.I),
    ),
    (
        "jailbreak",
        re.compile(r"jailbreak", re.I),
    ),
    (
        "im_start",
        re.compile(r"<\|im_start\|>"),
    ),
    (
        "inst_tag",
        re.compile(r"\[INST\]"),
    ),
]


def detect_injection(text: str) -> bool:
    """Return ``True`` if *text* contains a prompt-injection pattern.

    On detection, a structured warning is emitted with the *pattern name*
    only — the raw input is never written to the log.

    Parameters
    ----------
    text:
        The string to scan (e.g. user query or LLM-generated output).

    Returns
    -------
    bool
        ``True`` if any injection pattern matched; ``False`` otherwise.
    """
    for name, pattern in INJECTION_PATTERNS:
        if pattern.search(text):
            logger.warning("injection_pattern_detected", pattern_name=name)
            return True
    return False
