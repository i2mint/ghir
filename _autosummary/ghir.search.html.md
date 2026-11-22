# ghir.search

### ghir.search(query, , k=20, rank='ir', extract=None, store=None, local_roots=None, include_forks=True, include_archived=True, \*\*rank_kw)

Rank cached repos for `query`; each hit says where it is cloned, if anywhere.

Offline: reads the cache filled by [`ghir.cache.refresh()`](ghir.cache.html.md#ghir.cache.refresh).

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`RepoHit`](ghir.html.md#ghir.RepoHit)]
