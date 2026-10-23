"""Fetching repo records from GitHub, through the ``gh`` CLI's GraphQL access.

One GraphQL page returns up to :data:`DFLT_PAGE_SIZE` repos *with* their README
text, so a whole organization costs a handful of calls rather than one per repo.

The transport is a seam: every function takes ``graphql=``, a callable
``(query, variables) -> dict``. The default shells out to ``gh api graphql``
(so authentication is whatever ``gh auth login`` set up); tests pass a fake.

A *location* is one of:

- an owner login (``"i2mint"``): every repo of that user or organization;
- ``"@me"``: the authenticated user and every organization they belong to;
- ``"search:<query>"``: the repos a GitHub search returns
  (``"search:user:thorwhalen topic:education"``).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable, Iterable, Iterator, Mapping
from fnmatch import fnmatch
from typing import Any

GraphQL = Callable[[str, Mapping[str, Any]], dict]

DFLT_PAGE_SIZE = 25
#: On a gateway error (README blobs make pages slow), the page size is halved
#: down to this before the error is let through.
MIN_PAGE_SIZE = 3
_TRANSIENT = ("HTTP 502", "HTTP 503", "HTTP 504", "timeout", "Timeout")
#: README file names tried, in order, at the default branch's root.
README_NAMES = ("README.md", "readme.md", "README.rst", "README", "README.txt")
SEARCH_PREFIX = "search:"
ME = "@me"

_README_FIELDS = "\n".join(
    f'readme{i}: object(expression: "HEAD:{n}") {{ ... on Blob {{ text }} }}'
    for i, n in enumerate(README_NAMES)
)

REPO_FIELDS = f"""
nameWithOwner name description url homepageUrl isFork isArchived isPrivate
pushedAt updatedAt stargazerCount
primaryLanguage {{ name }}
repositoryTopics(first: 20) {{ nodes {{ topic {{ name }} }} }}
{_README_FIELDS}
"""

OWNER_QUERY = f"""
query($owner: String!, $after: String, $n: Int!) {{
  repositoryOwner(login: $owner) {{
    repositories(first: $n, after: $after, ownerAffiliations: OWNER) {{
      pageInfo {{ hasNextPage endCursor }}
      nodes {{ {REPO_FIELDS} }}
    }}
  }}
}}
"""

SEARCH_QUERY = f"""
query($q: String!, $after: String, $n: Int!) {{
  search(type: REPOSITORY, query: $q, first: $n, after: $after) {{
    pageInfo {{ hasNextPage endCursor }}
    nodes {{ ... on Repository {{ {REPO_FIELDS} }} }}
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


def normalize_repo(node: Mapping[str, Any]) -> dict:
    """Flatten one GraphQL repository node into a JSON-friendly record.

    >>> normalize_repo({"nameWithOwner": "a/b", "name": "b",
    ...     "primaryLanguage": {"name": "Python"},
    ...     "repositoryTopics": {"nodes": [{"topic": {"name": "x"}}]},
    ...     "readme0": None, "readme1": {"text": "hi"}})["readme"]
    'hi'
    """
    readme = next(
        (
            node[f"readme{i}"]["text"]
            for i in range(len(README_NAMES))
            if (node.get(f"readme{i}") or {}).get("text")
        ),
        "",
    )
    owner, _, name = node["nameWithOwner"].partition("/")
    return {
        "id": node["nameWithOwner"],
        "owner": owner,
        "name": name,
        "description": node.get("description") or "",
        "url": node.get("url") or f"https://github.com/{node['nameWithOwner']}",
        "homepage": node.get("homepageUrl") or "",
        "language": (node.get("primaryLanguage") or {}).get("name") or "",
        "topics": [
            t["topic"]["name"]
            for t in (node.get("repositoryTopics") or {}).get("nodes", [])
        ],
        "is_fork": bool(node.get("isFork")),
        "is_archived": bool(node.get("isArchived")),
        "is_private": bool(node.get("isPrivate")),
        "pushed_at": node.get("pushedAt") or "",
        "updated_at": node.get("updatedAt") or "",
        "stars": node.get("stargazerCount") or 0,
        "readme": readme,
    }


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


def fetch_location(
    location: str,
    *,
    graphql: GraphQL = gh_graphql,
    page_size: int = DFLT_PAGE_SIZE,
) -> Iterator[dict]:
    """Yield normalized repo records for one owner login or ``search:`` spec."""
    if location.startswith(SEARCH_PREFIX):
        q = location[len(SEARCH_PREFIX) :].strip()
        nodes = _paginate(SEARCH_QUERY, {"q": q, "n": page_size}, "search", graphql)
    else:
        nodes = _paginate(
            OWNER_QUERY,
            {"owner": location, "n": page_size},
            "repositoryOwner.repositories",
            graphql,
        )
    yield from map(normalize_repo, nodes)


def expand_locations(
    locations: Iterable[str], *, owners: Callable[[], list[str]] = my_owners
) -> list[str]:
    """Replace ``"@me"`` by the user's owners; keep order, drop duplicates."""
    out: list[str] = []
    for loc in locations:
        for item in owners() if loc == ME else [loc]:
            if item not in out:
                out.append(item)
    return out


def is_excluded(repo_id: str, exclude: Iterable[str]) -> bool:
    """Whether ``owner/name`` matches any fnmatch pattern of ``exclude``.

    >>> is_excluded("Acme/x", ["acme/*"]), is_excluded("i2mint/x", ["acme/*"])
    (True, False)
    """
    rid = repo_id.lower()
    return any(fnmatch(rid, p.lower()) for p in exclude)


def fetch_repos(
    locations: Iterable[str],
    *,
    exclude: Iterable[str] = (),
    graphql: GraphQL = gh_graphql,
    owners: Callable[[], list[str]] = my_owners,
    on_error: Callable[[str, Exception], None] | None = None,
) -> Iterator[dict]:
    """Yield repo records over all ``locations``, skipping excluded repos.

    A location whose fetch fails is passed to ``on_error(location, error)`` and
    skipped, or, when ``on_error`` is None, the error propagates.

    An owner pattern in ``exclude`` (``"Acme/*"``) also stops that owner from
    being queried at all, so nothing of it is fetched.
    """
    exclude = list(exclude)
    for loc in expand_locations(locations, owners=owners):
        if not loc.startswith(SEARCH_PREFIX) and is_excluded(f"{loc}/*", exclude):
            continue
        try:
            for rec in fetch_location(loc, graphql=graphql):
                if not is_excluded(rec["id"], exclude):
                    yield rec
        except RuntimeError as e:
            if on_error is None:
                raise
            on_error(loc, e)
