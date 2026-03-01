"""Conflict resolution and deduplication for the semantic store.

Prevents contradictions in ``memory.md`` by detecting when a new entry
supersedes an existing one (e.g., "Preset: balanced" → "Preset: accurate").

Uses a simple heuristic: if the new entry and an existing entry share
2+ significant words (excluding stopwords), they likely refer to the same
topic and the old entry should be replaced.
"""

from __future__ import annotations

import re

# Minimum number of shared significant words to consider entries related.
_MIN_SHARED_WORDS = 2

# Stopwords for matching (French + English, minimal set).
_STOPWORDS = frozenset(
    "le la les un une des de du au aux et ou en à par pour dans sur "
    "avec est ce cette que qui ne pas se son sa ses leur "
    "the a an and or in on at to for with is are was were of from by not".split()
)


def find_conflicting_entry(existing_entries: list[str], new_entry: str) -> int | None:
    """Return the index of an entry that *new_entry* supersedes, or None.

    Strips date stamps like ``[2026-03-01]`` and leading ``- `` before
    comparing.
    """
    new_words = _significant_words(new_entry)
    if len(new_words) < _MIN_SHARED_WORDS:
        return None

    for i, entry in enumerate(existing_entries):
        existing_words = _significant_words(entry)
        shared = new_words & existing_words
        if len(shared) >= _MIN_SHARED_WORDS:
            return i

    return None


def consolidate_entry(existing_entries: list[str], new_entry: str) -> list[str]:
    """Return a new list with *new_entry* replacing any conflicting entry.

    If no conflict is found, *new_entry* is simply appended.
    """
    conflict_idx = find_conflicting_entry(existing_entries, new_entry)
    result = list(existing_entries)
    if conflict_idx is not None:
        result[conflict_idx] = new_entry
    else:
        result.append(new_entry)
    return result


def _significant_words(text: str) -> set[str]:
    """Extract significant words from an entry (lowercase, ≥3 chars, no stopwords)."""
    # Strip date stamps like [2026-03-01] and leading "- "
    cleaned = re.sub(r"\[\d{4}-\d{2}-\d{2}\]\s*", "", text)
    cleaned = cleaned.lstrip("- ").strip()
    return {
        w for w in re.findall(r"\b\w{3,}\b", cleaned.lower()) if w not in _STOPWORDS
    }
