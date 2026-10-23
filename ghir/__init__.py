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

from .cache import refresh, repo_store
from .config import settings
from .extract import extractors
from .fetch import fetch_repos
from .local import local_clones
from .search import (
    RepoHit,
    grep_rank,
    ir_rank,
    rankers,
    records,
    register_corpus,
    search,
)

__all__ = [
    "RepoHit",
    "extractors",
    "fetch_repos",
    "grep_rank",
    "ir_rank",
    "local_clones",
    "rankers",
    "records",
    "refresh",
    "register_corpus",
    "repo_store",
    "search",
    "settings",
]
