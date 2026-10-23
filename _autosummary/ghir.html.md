# ghir

Search your GitHub repos, cloned or not, as an `ir` corpus.

Four seams, each a keyword argument with a working default:

- **locations** ([`refresh()`](#ghir.refresh)): owner logins, `"@me"` (you and your orgs),
  or `"search:<github query>"`.
- **extraction** (`extract=`): what text a repo contributes; default
  description + topics + README head ([`ghir.extract`](ghir.extract.html.md#module-ghir.extract)).
- **ranking** (`rank=`): `"ir"` (default, hybrid dense + BM25) or `"grep"`.
- **cache** (`store=`): a `MutableMapping`; [`refresh()`](#ghir.refresh) merges into it,
  [`search()`](#ghir.search) only reads it (offline).

```pycon
>>> import ghir
>>> ghir.refresh()
>>> for hit in ghir.search("flashcards spaced repetition"):
...     print(hit.id, hit.local_path)
```

### Functions

| [`fetch_repos`](#ghir.fetch_repos)(locations, \*[, exclude, ...])         | Yield repo records over all `locations`, skipping excluded repos.             |
|-----------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| [`grep_rank`](#ghir.grep_rank)(query, docs, \*[, k])                    | Fraction of query terms (as word prefixes) found in each repo's text.         |
| [`ir_rank`](#ghir.ir_rank)(query, docs, \*[, k, mode, embedder, ...]) | Rank with `ir`: build (incrementally) then `ir.search`.                       |
| [`local_clones`](#ghir.local_clones)(roots, \*[, max_depth])               | `{"owner/name" (lowercased): path}` for git checkouts under `roots`.          |
| [`records`](#ghir.records)()                                          | The default records, as a zero-argument fetcher for ir's registry.            |
| [`refresh`](#ghir.refresh)([locations, store, exclude, fetch])        | Fetch the repos of `locations` and merge them into the cache.                 |
| [`register_corpus`](#ghir.register_corpus)([name])                            | Register the cache as an ir corpus, so `ir discover <name> ...` works.        |
| [`repo_store`](#ghir.repo_store)([cache_dir])                            | The default cache: `{"owner/name": record}` over JSON files.                  |
| [`search`](#ghir.search)(query, \*[, k, rank, extract, store, ...])  | Rank cached repos for `query`; each hit says where it is cloned, if anywhere. |
| [`settings`](#ghir.settings)([path])                                   | The effective settings: defaults, then the config file, then `overrides`.     |

### Classes

| [`RepoHit`](#ghir.RepoHit)(id, score, description, url[, ...])   | One search result: a repo, its score, and where it is cloned (if it is).   |
|------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------|

### *class* ghir.RepoHit(id, score, description, url, language='', local_path=None, is_fork=False, is_archived=False)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

One search result: a repo, its score, and where it is cloned (if it is).

### ghir.fetch_repos(locations, \*, exclude=(), graphql=<function gh_graphql>, owners=<function my_owners>, on_error=None)

Yield repo records over all `locations`, skipping excluded repos.

A location whose fetch fails is passed to `on_error(location, error)` and
skipped, or, when `on_error` is None, the error propagates.

An owner pattern in `exclude` (`"Acme/*"`) also stops that owner from
being queried at all, so nothing of it is fetched.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]

### ghir.grep_rank(query, docs, , k=20, \*\*\_)

Fraction of query terms (as word prefixes) found in each repo’s text.

```pycon
>>> docs = {"a/x": {"text": "Spaced repetition flashcards"},
...         "a/y": {"text": "audio tools"}}
>>> grep_rank("flashcard spaced", docs)
[('a/x', 1.0)]
```

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`float`](https://docs.python.org/3/builtins/functions.html#float)]]

### ghir.ir_rank(query, docs, , k=20, corpus_name, mode='hybrid', embedder='default', ir_store=None, \*\*search_kw)

Rank with `ir`: build (incrementally) then `ir.search`.

`docs` maps repo id to an ir record (`{"id", "text", ...metadata}`).
`ir_store` is the ir `CorpusStore` (default: ir’s local store, named
`corpus_name`); other keyword arguments go to `ir.search`.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`float`](https://docs.python.org/3/builtins/functions.html#float)]]

### ghir.local_clones(roots, , max_depth=3)

`{"owner/name" (lowercased): path}` for git checkouts under `roots`.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### ghir.records()

The default records, as a zero-argument fetcher for ir’s registry.

`ir.register("gh_repos", "records", fetcher="ghir:records")` makes the
cache searchable with ir’s own CLI (`ir discover gh_repos "..."`).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]

### ghir.refresh(locations=None, \*, store=None, exclude=None, fetch=<function fetch_repos>, \*\*fetch_kwargs)

Fetch the repos of `locations` and merge them into the cache.

Returns counts: `{"fetched", "added", "updated", "kept"}` where `kept` is
the number of cached records this fetch did not see (and left alone), plus
`"failed"`: `{location: error}` for locations that could not be fetched
(their cached records are kept), and `"purged"`: cached records removed
because they are now excluded (by `exclude` or `local_exclude`).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### ghir.register_corpus(name=None)

Register the cache as an ir corpus, so `ir discover <name> ...` works.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### ghir.repo_store(cache_dir=None)

The default cache: `{"owner/name": record}` over JSON files.

* **Return type:**
  [`MutableMapping`](https://docs.python.org/3/library/collections.abc.html#collections.abc.MutableMapping)

### ghir.search(query, , k=20, rank='ir', extract=None, store=None, local_roots=None, include_forks=True, include_archived=True, \*\*rank_kw)

Rank cached repos for `query`; each hit says where it is cloned, if anywhere.

Offline: reads the cache filled by [`ghir.cache.refresh()`](ghir.cache.html.md#ghir.cache.refresh).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`RepoHit`](#ghir.RepoHit)]

### ghir.settings(path=None, \*\*overrides)

The effective settings: defaults, then the config file, then `overrides`.

```pycon
>>> s = settings(path="/nonexistent/ghir.json", exclude=["acme/*"])
>>> s["exclude"], s["locations"]
(['acme/*'], ['@me'])
```

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### Modules

| [`cache`](ghir.cache.html.md#module-ghir.cache)     | The repo-record cache: a `MutableMapping` from `owner/name` to a record.   |
|------------------------------------------------------------------------------|----------------------------------------------------------------------------|
| [`config`](ghir.config.html.md#module-ghir.config)   | Settings for ghir: where the cache lives and which repos are in scope.     |
| [`extract`](ghir.extract.html.md#module-ghir.extract) | Extraction: what text each cached repo contributes to the search.          |
| [`fetch`](ghir.fetch.html.md#module-ghir.fetch)     | Fetching repo records from GitHub, through the `gh` CLI's GraphQL access.  |
| [`local`](ghir.local.html.md#module-ghir.local)     | Which GitHub repos are cloned on this machine, and where.                  |
