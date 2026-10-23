"""Extraction: what text each cached repo contributes to the search.

An extractor is a function ``record -> str``. :data:`extractors` names the
built-in ones; any callable works wherever an extractor is accepted. The text
returned is what gets indexed and ranked, so it decides what a query can match.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

Extractor = Callable[[Mapping[str, Any]], str]

#: README characters kept by the default extractor (READMEs can be huge, and
#: their opening says what the repo is).
DFLT_README_CHARS = 6000


def _head(rec: Mapping[str, Any]) -> list[str]:
    topics = " ".join(rec.get("topics") or ())
    return [
        rec.get("name", ""),
        rec.get("description", ""),
        f"topics: {topics}" if topics else "",
    ]


def description(rec: Mapping[str, Any]) -> str:
    """Name, description and topics.

    >>> description({"name": "learny", "description": "Learner models",
    ...              "topics": ["education"]})
    'learny\\nLearner models\\ntopics: education'
    """
    return "\n".join(p for p in _head(rec) if p)


def description_and_readme(
    rec: Mapping[str, Any], *, readme_chars: int = DFLT_README_CHARS
) -> str:
    """Name, description, topics, and the start of the README (the default)."""
    readme = (rec.get("readme") or "")[:readme_chars]
    return "\n".join(p for p in [*_head(rec), readme] if p)


extractors: dict[str, Extractor] = {
    "description": description,
    "description_and_readme": description_and_readme,
}


def resolve_extractor(extract: str | Extractor) -> Extractor:
    """An extractor from its name in :data:`extractors`, or a callable as is."""
    if callable(extract):
        return extract
    try:
        return extractors[extract]
    except KeyError:
        raise ValueError(
            f"Unknown extractor {extract!r}; use a callable or one of "
            f"{sorted(extractors)}"
        ) from None
