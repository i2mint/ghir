"""Owner logins -> repo records, stdlib only (no ``ir``, no ``dol``).

The reusable half of :mod:`ghir.fetch`: a GraphQL transport seam (``graphql=``,
a callable ``(query, variables) -> dict``; :func:`gh_graphql` shells out to the
``gh`` CLI, :func:`urllib_graphql` needs only a token), ``"@me"`` expansion,
fnmatch exclusion and cursor pagination that backs off the page size on gateway
errors. What a record *contains* is a seam too: ``fields`` is the GraphQL
selection and ``normalize`` flattens a node, so ghir asks for README blobs while
another collector asks for permissions and fork counts.

>>> expand_owners(["@me", "acme", "bob"], me=lambda: ["bob", "org1"])
['bob', 'org1', 'acme']
>>> is_excluded("Acme/x", ["acme/*"]), is_excluded("bob/x", ["acme/*"])
(True, False)
>>> def fake(query, variables):
...     return {"repositoryOwner": {"repositories": {
...         "pageInfo": {"hasNextPage": False, "endCursor": None},
...         "nodes": [{"nameWithOwner": "acme/x"}, {"nameWithOwner": "acme/y"}]}}}
>>> [r["nameWithOwner"] for r in list_repos(["acme"], graphql=fake, exclude=["acme/y"])]
['acme/x']
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Iterator, Mapping
from fnmatch import fnmatch
from typing import Any

GraphQL = Callable[[str, Mapping[str, Any]], dict]

DFLT_PAGE_SIZE = 25
#: On a gateway error, the page size is halved down to this before the error is let through.
MIN_PAGE_SIZE = 3
_TRANSIENT = ("HTTP 502", "HTTP 503", "HTTP 504", "timeout", "Timeout")
ME = "@me"
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
#: The least a repo listing needs; pass a richer ``fields=`` selection to ask for more.
DFLT_FIELDS = "nameWithOwner name description url isFork isArchived isPrivate"

OWNER_QUERY_TEMPLATE = """
query($owner: String!, $after: String, $n: Int!) {{
  repositoryOwner(login: $owner) {{
    repositories(first: $n, after: $after, ownerAffiliations: OWNER) {{
      pageInfo {{ hasNextPage endCursor }}
      nodes {{ {fields} }}
    }}
  }}
}}
"""


def gh_graphql(query: str, variables: Mapping[str, Any]) -> dict:
    """Run a GraphQL query through ``gh api graphql`` and return its ``data``."""
    if not shutil.which("gh"):
        raise RuntimeError(
            "ghir fetches through the GitHub CLI, which is not on PATH. "
            "Install it (https://cli.github.com) and run `gh auth login`."
        )
    args = ["gh", "api", "graphql", "-f", f"query={query}"]
    for k, v in variables.items():
        if v is not None:
            args += ["-F" if isinstance(v, int) else "-f", f"{k}={v}"]
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"gh api graphql failed: {proc.stderr.strip()}")
    payload = json.loads(proc.stdout)
    if payload.get("errors") and not payload.get("data"):
        raise RuntimeError(f"GitHub GraphQL errors: {payload['errors']}")
    return payload["data"]


def gh_api(path: str) -> Any:
    """``gh api <path>`` (REST), JSON-decoded."""
    proc = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"gh api {path} failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def my_owners(*, rest: Callable[[str], Any] = gh_api) -> list[str]:
    """The authenticated user's login followed by their organizations' logins."""
    return [rest("user")["login"]] + [o["login"] for o in rest("user/orgs")]


def urllib_graphql(
    token: str | None = None, *, url: str = GITHUB_GRAPHQL_URL, timeout: float = 60
) -> GraphQL:
    """A GraphQL transport over ``urllib`` and a token (default ``$GITHUB_TOKEN``/``$GH_TOKEN``).

    For environments without the ``gh`` CLI (a GitHub Action, a container).
    """

    def graphql(query: str, variables: Mapping[str, Any]) -> dict:
        tok = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not tok:
            raise RuntimeError(
                "urllib_graphql needs a token (argument or $GITHUB_TOKEN)."
            )
        req = urllib.request.Request(
            url,
            data=json.dumps({"query": query, "variables": dict(variables)}).encode(),
            headers={
                "Authorization": f"Bearer {tok}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.load(resp)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"GitHub GraphQL HTTP {e.code}: {e.reason}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            raise RuntimeError(f"GitHub GraphQL timeout/network error: {e}") from e
        if payload.get("errors") and not payload.get("data"):
            raise RuntimeError(f"GitHub GraphQL errors: {payload['errors']}")
        return payload["data"]

    return graphql


def _query_page(query: str, variables: dict, graphql: GraphQL) -> dict:
    n = variables["n"]
    while True:
        try:
            return graphql(query, {**variables, "n": n})
        except RuntimeError as e:
            if n <= MIN_PAGE_SIZE or not any(s in str(e) for s in _TRANSIENT):
                raise
            n = max(MIN_PAGE_SIZE, n // 2)


def _paginate(query: str, variables: dict, path: str, graphql: GraphQL):
    after = None
    while True:
        data = _query_page(query, {**variables, "after": after}, graphql)
        for key in path.split("."):
            data = data[key] if data else None
        if not data:  # unknown owner, say
            return
        yield from (n for n in data["nodes"] if n and n.get("nameWithOwner"))
        if not data["pageInfo"]["hasNextPage"]:
            return
        after = data["pageInfo"]["endCursor"]


def expand_owners(owners: Iterable[str], *, me: Callable[[], list[str]]) -> list[str]:
    """Replace ``"@me"`` by the user's owners; keep order, drop case-insensitive duplicates."""
    out: list[str] = []
    for owner in owners:
        for item in me() if owner == ME else [owner]:
            if item.lower() not in (o.lower() for o in out):
                out.append(item)
    return out


def is_excluded(repo_id: str, exclude: Iterable[str]) -> bool:
    """Whether ``owner/name`` matches any fnmatch pattern of ``exclude``.

    >>> is_excluded("Acme/x", ["acme/*"]), is_excluded("i2mint/x", ["acme/*"])
    (True, False)
    """
    rid = repo_id.lower()
    return any(fnmatch(rid, p.lower()) for p in exclude)


def owner_is_excluded(owner: str, exclude: Iterable[str]) -> bool:
    """Whether some pattern of ``exclude`` matches *every* repo of ``owner``.

    Only a pattern ending in ``*`` whose head matches ``"<owner>/"`` does
    (``"acme/*"``, ``"*/*"``); ``"acme/?"`` or ``"acme/[!l]*"`` exclude only
    some of acme's repos, so acme must still be listed.

    >>> owner_is_excluded("Acme", ["acme/*"]), owner_is_excluded("acme", ["acme/?"])
    (True, False)
    """
    prefix = f"{owner}/".lower()
    return any(
        p.endswith("*") and fnmatch(prefix, p.rstrip("*").lower()) for p in exclude
    )


def owner_nodes(
    owner: str,
    *,
    graphql: GraphQL = gh_graphql,
    fields: str = DFLT_FIELDS,
    page_size: int = DFLT_PAGE_SIZE,
) -> Iterator[dict]:
    """Yield the raw GraphQL nodes of every repo owned by ``owner`` (``fields`` selects them)."""
    yield from _paginate(
        OWNER_QUERY_TEMPLATE.format(fields=fields),
        {"owner": owner, "n": page_size},
        "repositoryOwner.repositories",
        graphql,
    )


def list_repos(
    owners: Iterable[str],
    *,
    graphql: GraphQL = gh_graphql,
    fields: str = DFLT_FIELDS,
    normalize: Callable[[Mapping[str, Any]], Any] | None = None,
    exclude: Iterable[str] = (),
    me: Callable[[], list[str]] = my_owners,
    page_size: int = DFLT_PAGE_SIZE,
    on_error: Callable[[str, Exception], None] | None = None,
) -> Iterator[Any]:
    """Yield a record per repo over ``owners`` (``"@me"`` expanded), minus ``exclude``.

    ``normalize`` maps a node to the record (default: the node itself). An owner
    pattern in ``exclude`` (``"acme/*"``) also stops that owner being queried. An
    owner whose listing fails goes to ``on_error(owner, error)`` and is skipped,
    or, when ``on_error`` is None, the error propagates.
    """
    exclude = list(exclude)
    for owner in expand_owners(owners, me=me):
        if owner_is_excluded(owner, exclude):
            continue
        try:
            for node in owner_nodes(
                owner, graphql=graphql, fields=fields, page_size=page_size
            ):
                if not is_excluded(node["nameWithOwner"], exclude):
                    yield node if normalize is None else normalize(node)
        except RuntimeError as e:
            if on_error is None:
                raise
            on_error(owner, e)
