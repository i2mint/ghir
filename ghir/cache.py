"""The repo-record cache: a ``MutableMapping`` from ``owner/name`` to a record.

Searching never goes online; it reads this cache. :func:`refresh` is the only
thing that fetches, and it *merges*: fetched records overwrite their own keys,
records not seen this time are kept (a repo outside today's locations, or a
fetch that failed half-way, does not erase what was known). Each record carries
``fetched_at`` so staleness is visible.

The store is a seam (``store=``): the default is one JSON file per repo under
:data:`ghir.config.DFLT_CACHE_DIR` (a ``dol`` store, so an S3 or database
mapping drops in unchanged).
"""

from __future__ import annotations

from collections.abc import Iterable, MutableMapping
from datetime import datetime, timezone
from pathlib import Path

from dol import JsonFiles, mk_dirs_if_missing, wrap_kvs

from .config import ir_excluded_patterns
from .config import settings as _settings
from .fetch import fetch_repos, is_excluded
from .local import excluded_clones, local_clones

#: Repo ids contain a "/", which becomes a directory level (owner/name.json).
_EXT = ".json"


def repo_store(cache_dir: str | Path | None = None) -> MutableMapping:
    """The default cache: ``{"owner/name": record}`` over JSON files."""
    root = Path(cache_dir or _settings()["cache_dir"])
    root.mkdir(parents=True, exist_ok=True)
    return wrap_kvs(
        mk_dirs_if_missing(JsonFiles(str(root))),
        id_of_key=lambda k: k + _EXT,
        key_of_id=lambda _id: _id[: -len(_EXT)],
    )


def excluded_ids(s: dict, *, clones: dict | None = None) -> set[str]:
    """Lowercased ids of locally cloned repos under a ``local_exclude`` pattern."""
    patterns = s["local_exclude"]
    patterns = ir_excluded_patterns() if patterns is None else patterns
    if not patterns:
        return set()
    clones = local_clones(s["local_roots"]) if clones is None else clones
    return excluded_clones(clones, patterns, roots=s["local_roots"])


def refresh(
    locations: Iterable[str] | None = None,
    *,
    store: MutableMapping | None = None,
    exclude: Iterable[str] | None = None,
    fetch=fetch_repos,
    **fetch_kwargs,
) -> dict:
    """Fetch the repos of ``locations`` and merge them into the cache.

    Returns counts: ``{"fetched", "added", "updated", "kept"}`` where ``kept`` is
    the number of cached records this fetch did not see (and left alone), plus
    ``"failed"``: ``{location: error}`` for locations that could not be fetched
    (their cached records are kept), and ``"purged"``: cached records removed
    because they are now excluded (by ``exclude`` or ``local_exclude``).
    """
    s = _settings(locations=locations, exclude=exclude)
    store = repo_store(s["cache_dir"]) if store is None else store
    exclude = [*s["exclude"], *excluded_ids(s)]
    purged = [rid for rid in list(store) if is_excluded(rid, exclude)]
    for rid in purged:
        del store[rid]
    before = set(store)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    seen, failed = set(), {}
    fetch_kwargs.setdefault("on_error", lambda loc, e: failed.update({loc: str(e)}))
    for rec in fetch(s["locations"], exclude=exclude, **fetch_kwargs):
        store[rec["id"]] = {**rec, "fetched_at": now}
        seen.add(rec["id"])
    return {
        "fetched": len(seen),
        "added": len(seen - before),
        "updated": len(seen & before),
        "kept": len(before - seen),
        "failed": failed,
        "purged": len(purged),
    }
