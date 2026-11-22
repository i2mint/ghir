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

from collections.abc import Callable, Iterable, Iterator, Mapping
from typing import Any

from .owners import (  # noqa: F401  (re-exported: the historical home of these names)
    DFLT_PAGE_SIZE,
    ME,
    MIN_PAGE_SIZE,
    GraphQL,
    _paginate,
    expand_owners,
    gh_api,
    gh_graphql,
    is_excluded,
    my_owners,
    owner_nodes,
)

#: README file names tried, in order, at the default branch's root.
README_NAMES = ("README.md", "readme.md", "README.rst", "README", "README.txt")
SEARCH_PREFIX = "search:"

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

SEARCH_QUERY = f"""
query($q: String!, $after: String, $n: Int!) {{
  search(type: REPOSITORY, query: $q, first: $n, after: $after) {{
    pageInfo {{ hasNextPage endCursor }}
    nodes {{ ... on Repository {{ {REPO_FIELDS} }} }}
  }}
}}
"""


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
        nodes = owner_nodes(
            location, graphql=graphql, fields=REPO_FIELDS, page_size=page_size
        )
    yield from map(normalize_repo, nodes)


def expand_locations(
    locations: Iterable[str], *, owners: Callable[[], list[str]] = my_owners
) -> list[str]:
    """Replace ``"@me"`` by the user's owners; keep order, drop duplicates."""
    return expand_owners(locations, me=owners)


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
