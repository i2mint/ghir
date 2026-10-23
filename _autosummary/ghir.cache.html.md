# ghir.cache

The repo-record cache: a `MutableMapping` from `owner/name` to a record.

Searching never goes online; it reads this cache. [`refresh()`](#ghir.cache.refresh) is the only
thing that fetches, and it *merges*: fetched records overwrite their own keys,
records not seen this time are kept (a repo outside today’s locations, or a
fetch that failed half-way, does not erase what was known). Each record carries
`fetched_at` so staleness is visible.

The store is a seam (`store=`): the default is one JSON file per repo under
[`ghir.config.DFLT_CACHE_DIR`](ghir.config.html.md#ghir.config.DFLT_CACHE_DIR) (a `dol` store, so an S3 or database
mapping drops in unchanged).

### Functions

| [`excluded_ids`](#ghir.cache.excluded_ids)(s, \*[, clones])               | Lowercased ids of locally cloned repos under a `local_exclude` pattern.   |
|----------------------------------------------------------------------------------------------|---------------------------------------------------------------------------|
| [`refresh`](#ghir.cache.refresh)([locations, store, exclude, fetch]) | Fetch the repos of `locations` and merge them into the cache.             |
| [`repo_store`](#ghir.cache.repo_store)([cache_dir])                     | The default cache: `{"owner/name": record}` over JSON files.              |

### ghir.cache.excluded_ids(s, , clones=None)

Lowercased ids of locally cloned repos under a `local_exclude` pattern.

* **Return type:**
  [`set`](https://docs.python.org/3/builtins/stdtypes.html#set)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### ghir.cache.refresh(locations=None, \*, store=None, exclude=None, fetch=<function fetch_repos>, \*\*fetch_kwargs)

Fetch the repos of `locations` and merge them into the cache.

Returns counts: `{"fetched", "added", "updated", "kept"}` where `kept` is
the number of cached records this fetch did not see (and left alone), plus
`"failed"`: `{location: error}` for locations that could not be fetched
(their cached records are kept), and `"purged"`: cached records removed
because they are now excluded (by `exclude` or `local_exclude`).

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### ghir.cache.repo_store(cache_dir=None)

The default cache: `{"owner/name": record}` over JSON files.

* **Return type:**
  [`MutableMapping`](https://docs.python.org/3/library/collections.abc.html#collections.abc.MutableMapping)
