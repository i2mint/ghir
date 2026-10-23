"""Hermetic tests: a fake GraphQL transport, a dict cache, the light embedder."""

import pytest

from ghir.cache import refresh
from ghir.fetch import fetch_repos
from ghir.local import local_clones
from ghir.search import grep_rank, search


def _node(owner, name, description="", readme=""):
    return {
        "nameWithOwner": f"{owner}/{name}",
        "name": name,
        "description": description,
        "readme0": {"text": readme} if readme else None,
    }


REPOS = {
    "acme": [
        _node("acme", "cards", "Flashcards with spaced repetition"),
        _node("acme", "beats", "Drum machine", readme="Make loops and beats."),
        _node("acme", "secret", "Do not fetch"),
    ],
    "other": [_node("other", "tutor", "Adaptive tutoring for kids")],
    "banned": [_node("banned", "x", "Must never be queried")],
}


def fake_graphql(pages=REPOS, page_size_seen=None):
    queried = []

    def graphql(query, variables):
        if "search(" in query:
            nodes = [n for ns in pages.values() for n in ns if "tutor" in n["name"]]
            return {"search": {"pageInfo": {"hasNextPage": False}, "nodes": nodes}}
        owner = variables["owner"]
        queried.append(owner)
        nodes = pages.get(owner)
        if nodes is None:
            return {"repositoryOwner": None}
        after = int(variables.get("after") or 0)
        n = variables["n"]
        chunk = nodes[after : after + n]
        more = after + n < len(nodes)
        return {
            "repositoryOwner": {
                "repositories": {
                    "pageInfo": {"hasNextPage": more, "endCursor": str(after + n)},
                    "nodes": chunk,
                }
            }
        }

    graphql.queried = queried
    return graphql


def test_fetch_paginates_expands_me_and_excludes():
    gq = fake_graphql()
    recs = list(
        fetch_repos(
            ["@me", "banned", "search:tutor"],
            exclude=["acme/secret", "banned/*"],
            graphql=gq,
            owners=lambda: ["acme", "other"],
        )
    )
    ids = [r["id"] for r in recs]
    assert ids == ["acme/cards", "acme/beats", "other/tutor", "other/tutor"]
    assert "banned" not in gq.queried  # an excluded owner is never queried
    assert recs[1]["readme"] == "Make loops and beats."


def test_fetch_halves_page_size_on_gateway_error():
    inner = fake_graphql()
    sizes = []

    def flaky(query, variables):
        sizes.append(variables["n"])
        if variables["n"] > 5:
            raise RuntimeError("gh api graphql failed: gh: HTTP 502")
        return inner(query, variables)

    recs = list(fetch_repos(["acme"], graphql=flaky, owners=list))
    assert len(recs) == 3 and sizes[:3] == [25, 12, 6]


def test_refresh_merges_and_keeps_unseen(tmp_path, monkeypatch):
    monkeypatch.setenv("GHIR_CONFIG", str(tmp_path / "none.json"))
    store = {"gone/old": {"id": "gone/old", "description": "kept"}}
    counts = refresh(
        ["acme", "missing"], store=store, graphql=fake_graphql(), owners=list
    )
    assert counts == {
        "fetched": 3,
        "added": 3,
        "updated": 0,
        "kept": 1,
        "failed": {},
    }
    assert "gone/old" in store and store["acme/cards"]["fetched_at"]


def test_refresh_records_failed_locations(tmp_path, monkeypatch):
    monkeypatch.setenv("GHIR_CONFIG", str(tmp_path / "none.json"))

    def broken(query, variables):
        raise RuntimeError("gh api graphql failed: HTTP 401")

    counts = refresh(["acme"], store={}, graphql=broken, owners=list)
    assert counts["fetched"] == 0 and "HTTP 401" in counts["failed"]["acme"]


def test_local_clones(tmp_path):
    repo = tmp_path / "t" / "cards" / ".git"
    repo.mkdir(parents=True)
    (repo / "config").write_text(
        '[remote "origin"]\n\turl = git@github.com:Acme/cards.git\n'
    )
    assert local_clones([tmp_path]) == {"acme/cards": str(repo.parent)}


@pytest.fixture
def filled(tmp_path, monkeypatch):
    monkeypatch.setenv("GHIR_CONFIG", str(tmp_path / "none.json"))
    store = {}
    refresh(["acme", "other"], store=store, graphql=fake_graphql(), owners=list)
    clone = tmp_path / "src" / "cards" / ".git"
    clone.mkdir(parents=True)
    (clone / "config").write_text("url = https://github.com/acme/cards\n")
    return store, tmp_path


def test_search_grep_marks_local(filled):
    store, root = filled
    hits = search(
        "spaced repetition", store=store, rank="grep", local_roots=[root / "src"]
    )
    assert [h.id for h in hits] == ["acme/cards"]
    assert hits[0].local_path == str(root / "src" / "cards")


def test_search_ir_light(filled):
    from ir.store import CorpusStore

    store, root = filled
    hits = search(
        "flashcards spaced repetition",
        k=2,
        store=store,
        local_roots=[root / "src"],
        embedder="light",
        ir_store=CorpusStore.memory(),
    )
    assert hits[0].id == "acme/cards" and hits[0].local_path


def test_grep_rank_empty_query():
    assert grep_rank("?", {"a/b": {"text": "x"}}) == []


def test_empty_cache_says_how_to_fill(tmp_path, monkeypatch):
    monkeypatch.setenv("GHIR_CONFIG", str(tmp_path / "none.json"))
    with pytest.raises(LookupError, match="ghir refresh"):
        search("x", store={})
