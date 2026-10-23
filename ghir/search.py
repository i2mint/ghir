"""Ranking cached repos against a query, and marking which ones are cloned here.

The ranking seam is ``rank=``, a callable ``(query, docs, *, k, **kw) -> [(id,
score)]`` over ``docs = {repo_id: text}``. Two are built in:

- :func:`ir_rank` (default): indexes the docs as an ``ir`` corpus (incremental:
  only changed repos are re-embedded) and runs ``ir.search``, hybrid by default.
- :func:`grep_rank`: no index, no model; scores a repo by how many query terms
  its text contains. The by-hand ``rg`` over ``gh repo list``, made reusable.

Nothing here touches the network: :func:`search` reads the cache that
:func:`ghir.cache.refresh` fills.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping, MutableMapping
from dataclasses import asdict, dataclass
from typing import Any

from .cache import repo_store
from .config import settings as _settings
from .extract import Extractor, resolve_extractor
from .local import local_clones

Ranker = Callable[..., list[tuple[str, float]]]

#: Record fields lifted into ir filter metadata (usable as ``filter=`` in ir).
METADATA_KEYS = ("owner", "language", "is_fork", "is_archived", "is_private")
DFLT_K = 20
DFLT_IR_MODE = "hybrid"


@dataclass(frozen=True)
class RepoHit:
    """One search result: a repo, its score, and where it is cloned (if it is)."""

    id: str
    score: float
    description: str
    url: str
    language: str = ""
    local_path: str | None = None
    is_fork: bool = False
    is_archived: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def ir_records(
    store: Mapping[str, Mapping] | None = None,
    *,
    extract: str | Extractor | None = None,
) -> list[dict]:
    """Cached repos as ir records: ``{"id", "text", <metadata keys>}``."""
    s = _settings(extract=extract)
    store = repo_store(s["cache_dir"]) if store is None else store
    fn = resolve_extractor(s["extract"])
    return [
        {"id": rid, "text": fn(rec), **{k: rec.get(k) for k in METADATA_KEYS}}
        for rid, rec in store.items()
    ]


def records() -> list[dict]:
    """The default records, as a zero-argument fetcher for ir's registry.

    ``ir.register("gh_repos", "records", fetcher="ghir:records")`` makes the
    cache searchable with ir's own CLI (``ir discover gh_repos "..."``).
    """
    return ir_records()


def _corpus_name(base: str, extract: str | Extractor) -> str:
    if extract == _settings()["extract"] and not callable(extract):
        return base
    tag = extract if isinstance(extract, str) else getattr(extract, "__name__", "fn")
    return f"{base}__{tag}"


def ir_rank(
    query: str,
    docs: Mapping[str, Mapping],
    *,
    k: int = DFLT_K,
    corpus_name: str,
    mode: str = DFLT_IR_MODE,
    embedder: Any = "default",
    ir_store: Any = None,
    **search_kw,
) -> list[tuple[str, float]]:
    """Rank with ``ir``: build (incrementally) then ``ir.search``.

    ``docs`` maps repo id to an ir record (``{"id", "text", ...metadata}``).
    ``ir_store`` is the ir ``CorpusStore`` (default: ir's local store, named
    ``corpus_name``); other keyword arguments go to ``ir.search``.
    """
    import ir

    source = ir.CorpusSource.from_records(
        name=corpus_name,
        fetcher=lambda: list(docs.values()),
        metadata_keys=METADATA_KEYS,
        embedder=embedder,
    )
    corpus = ir.build(source, store=ir_store)
    hits = ir.search(corpus, query, k=k, mode=mode, **search_kw)
    return [(h.artifact_id, float(h.score)) for h in hits]


def _terms(query: str) -> list[str]:
    return [t for t in re.split(r"\W+", query.lower()) if len(t) > 1]


def grep_rank(
    query: str, docs: Mapping[str, Mapping], *, k: int = DFLT_K, **_
) -> list[tuple[str, float]]:
    """Fraction of query terms (as word prefixes) found in each repo's text.

    >>> docs = {"a/x": {"text": "Spaced repetition flashcards"},
    ...         "a/y": {"text": "audio tools"}}
    >>> grep_rank("flashcard spaced", docs)
    [('a/x', 1.0)]
    """
    terms = _terms(query)
    if not terms:
        return []
    pats = [re.compile(rf"\b{re.escape(t)}", re.I) for t in terms]
    scored = [
        (rid, sum(bool(p.search(d["text"])) for p in pats) / len(pats))
        for rid, d in docs.items()
    ]
    scored = [x for x in scored if x[1] > 0]
    return sorted(scored, key=lambda x: -x[1])[:k]


rankers: dict[str, Ranker] = {"ir": ir_rank, "grep": grep_rank}


def search(
    query: str,
    *,
    k: int = DFLT_K,
    rank: str | Ranker = "ir",
    extract: str | Extractor | None = None,
    store: MutableMapping | None = None,
    local_roots: Iterable[str] | None = None,
    include_forks: bool = True,
    include_archived: bool = True,
    **rank_kw,
) -> list[RepoHit]:
    """Rank cached repos for ``query``; each hit says where it is cloned, if anywhere.

    Offline: reads the cache filled by :func:`ghir.cache.refresh`.
    """
    s = _settings(extract=extract, local_roots=local_roots)
    store = repo_store(s["cache_dir"]) if store is None else store
    if not len(store):
        raise LookupError(
            "The ghir cache is empty; fill it first with `ghir refresh` "
            "(or ghir.refresh())."
        )
    repos = {
        rid: rec
        for rid, rec in store.items()
        if (include_forks or not rec.get("is_fork"))
        and (include_archived or not rec.get("is_archived"))
    }
    docs = {r["id"]: r for r in ir_records(repos, extract=s["extract"])}
    ranker = rankers[rank] if isinstance(rank, str) else rank
    if ranker is ir_rank:
        rank_kw.setdefault("corpus_name", _corpus_name(s["corpus_name"], s["extract"]))
    ranked = ranker(query, docs, k=k, **rank_kw)
    clones = local_clones(s["local_roots"])
    return [
        RepoHit(
            id=rid,
            score=score,
            description=repos[rid].get("description", ""),
            url=repos[rid].get("url", ""),
            language=repos[rid].get("language", ""),
            local_path=clones.get(rid.lower()),
            is_fork=bool(repos[rid].get("is_fork")),
            is_archived=bool(repos[rid].get("is_archived")),
        )
        for rid, score in ranked
        if rid in repos
    ]


def register_corpus(name: str | None = None) -> dict:
    """Register the cache as an ir corpus, so ``ir discover <name> ...`` works."""
    import ir

    return ir.register(
        name or _settings()["corpus_name"],
        "records",
        fetcher="ghir:records",
        metadata_keys=list(METADATA_KEYS),
    )
