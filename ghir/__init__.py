"""Search your GitHub repos, cloned or not, as an ``ir`` corpus.

Four seams, each a keyword argument with a working default:

- **locations** (:func:`refresh`): owner logins, ``"@me"`` (you and your orgs),
  or ``"search:<github query>"``.
- **extraction** (``extract=``): what text a repo contributes; default
  description + topics + README head (:mod:`ghir.extract`).
- **ranking** (``rank=``): ``"ir"`` (default, hybrid dense + BM25) or ``"grep"``.
- **cache** (``store=``): a ``MutableMapping``; :func:`refresh` merges into it,
  :func:`search` only reads it (offline).

>>> import ghir  # doctest: +SKIP
>>> ghir.refresh()  # doctest: +SKIP
>>> for hit in ghir.search("flashcards spaced repetition"):  # doctest: +SKIP
...     print(hit.id, hit.local_path)
"""

from __future__ import annotations

import importlib

#: name -> submodule, resolved lazily so ``import ghir.owners`` stays stdlib-only
#: (``ir`` and ``dol`` are imported only when a search surface is first touched).
_LAZY = {
    "refresh": "cache",
    "repo_store": "cache",
    "settings": "config",
    "extractors": "extract",
    "fetch_repos": "fetch",
    "local_clones": "local",
    "RepoHit": "search",
    "grep_rank": "search",
    "ir_rank": "search",
    "rankers": "search",
    "records": "search",
    "register_corpus": "search",
    "search": "search",
}

__all__ = sorted(_LAZY)


def __getattr__(name):
    if name in _LAZY:
        value = getattr(importlib.import_module(f".{_LAZY[name]}", __name__), name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
