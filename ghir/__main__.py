"""Command line: ``ghir refresh`` (online, merges into the cache) and ``ghir search``.

.. code-block:: bash

    ghir refresh                                  # @me + config locations
    ghir refresh i2mint "search:user:thorwhalen topic:education"
    ghir search "flashcards spaced repetition"    # offline
    ghir search "audio tagging" --rank grep --local-only
"""

from __future__ import annotations

import argparse
import json
import sys

from .cache import refresh
from .search import DFLT_K, rankers, register_corpus, search


def _print_hits(hits, *, as_json: bool, local_only: bool):
    hits = [h for h in hits if h.local_path or not local_only]
    if as_json:
        print(json.dumps([h.to_dict() for h in hits], indent=2))
        return
    for h in hits:
        where = h.local_path or "(not cloned)"
        flags = "".join(
            f" [{f}]"
            for f, on in (("fork", h.is_fork), ("archived", h.is_archived))
            if on
        )
        print(f"{h.score:6.3f}  {h.id}{flags}  {where}")
        if h.description:
            print(f"        {h.description}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="ghir", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("refresh", help="fetch repos from GitHub, merge into the cache")
    r.add_argument("locations", nargs="*", help="owners, @me, or search:<query>")
    r.add_argument("--no-register", action="store_true", help="skip ir registration")

    s = sub.add_parser("search", help="rank cached repos for a query (offline)")
    s.add_argument("query")
    s.add_argument("-k", type=int, default=DFLT_K)
    s.add_argument("--rank", choices=sorted(rankers), default="ir")
    s.add_argument("--extract", default=None, help="extractor name")
    s.add_argument("--no-forks", action="store_true")
    s.add_argument("--no-archived", action="store_true")
    s.add_argument("--local-only", action="store_true", help="only cloned repos")
    s.add_argument("--json", action="store_true")

    a = p.parse_args(argv)
    if a.cmd == "refresh":
        counts = refresh(a.locations or None)
        if not a.no_register:
            register_corpus()
        print(json.dumps(counts))
        return 0
    hits = search(
        a.query,
        k=a.k,
        rank=a.rank,
        extract=a.extract,
        include_forks=not a.no_forks,
        include_archived=not a.no_archived,
    )
    _print_hits(hits, as_json=a.json, local_only=a.local_only)
    return 0


if __name__ == "__main__":
    sys.exit(main())
