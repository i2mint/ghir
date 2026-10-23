# ghir

Search your GitHub repos, cloned or not, across every organization you belong to. Fetch once, then search offline; each hit says where it is cloned on this machine, if anywhere.

```bash
pip install ghir
ghir refresh                                   # you + your orgs, through the gh CLI
ghir search "flashcards spaced repetition"     # offline, ranked by ir
```

```
 0.032  thorwhalen/tetrachord  /home/me/proj/tt/tetrachord
        Music education with a learner model and scheduler at the architectural centre.
 0.015  thorwhalen/rbxloop  (not cloned)
```

Requires the [GitHub CLI](https://cli.github.com) (`gh auth login`) for `refresh` only; searching never touches the network.

## The four seams

ghir is `corpus -> extraction -> ranking`, with a cache beside it. Each is one keyword argument with a working default.

| Seam | Argument | Default | Alternatives |
|---|---|---|---|
| Locations: which repos | `refresh(locations)` | `"@me"`: you and every org you belong to | owner logins, `"search:<github search query>"` |
| Extraction: what text a repo contributes | `extract=` | `"description_and_readme"` (name, description, topics, README head) | `"description"`, or any `record -> str` callable |
| Ranking | `rank=` | `"ir"`: hybrid dense + BM25 through [ir](https://github.com/i2mint/ir), indexed incrementally | `"grep"` (query terms as word prefixes, no index, no model), or any callable |
| Cache | `store=` | one JSON file per repo under `~/.local/share/ghir/repos/` | any `MutableMapping` (a `dol` store: S3, a database) |

`refresh` merges: fetched repos overwrite their own entries, and cached repos it did not see this time are kept. A location that fails to fetch is reported in `"failed"` and its cached repos stay.

```python
import ghir

ghir.refresh(["i2mint", "search:user:thorwhalen topic:education"])
for hit in ghir.search("audio tagging", rank="grep", include_forks=False):
    print(hit.id, hit.local_path or hit.url)
```

## Settings

Machine-specific choices go in `~/.config/ghir/config.json` (or `$GHIR_CONFIG`):

```json
{"locations": ["@me", "otosense"],
 "exclude": ["SomeClientOrg/*", "myorg/private-thing"]}
```

An owner excluded with `owner/*` is never queried. `local_exclude` takes patterns over local clone paths (`"q/private-repo"`); by default it is ir's own per-machine list, `~/.config/ir/exclude`, so a repo ir must not index is not fetched, cached or shown through GitHub either. A refresh purges cached repos that have become excluded. Other keys: `extract`, `local_roots` (where clones are looked for; default `$PP` or your home), `cache_dir`, `corpus_name`.

## Using it from ir

`ghir refresh` also registers the cache as the ir corpus `gh_repos` (a `records` corpus whose fetcher is `ghir:records`), so ir's own tools see it:

```bash
ir discover gh_repos "spaced repetition"
ir discover gh_repos packages "audio tagging"    # federated with the local packages corpus
```

Why this is a separate package and not part of ir: [docs/adr/0001-where-ghir-lives.md](docs/adr/0001-where-ghir-lives.md).
