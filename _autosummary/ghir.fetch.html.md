# ghir.fetch

Fetching repo records from GitHub, through the `gh` CLI’s GraphQL access.

One GraphQL page returns up to `DFLT_PAGE_SIZE` repos *with* their README
text, so a whole organization costs a handful of calls rather than one per repo.

The transport is a seam: every function takes `graphql=`, a callable
`(query, variables) -> dict`. The default shells out to `gh api graphql`
(so authentication is whatever `gh auth login` set up); tests pass a fake.

A *location* is one of:

- an owner login (`"i2mint"`): every repo of that user or organization;
- `"@me"`: the authenticated user and every organization they belong to;
- `"search:<query>"`: the repos a GitHub search returns
  (`"search:user:thorwhalen topic:education"`).

### Module Attributes

| [`README_NAMES`](#ghir.fetch.README_NAMES)   | README file names tried, in order, at the default branch's root.   |
|-----------------------------------------------------------------|--------------------------------------------------------------------|

### Functions

| [`expand_locations`](#ghir.fetch.expand_locations)(locations, \*[, owners])          | Replace `"@me"` by the user's owners; keep order, drop duplicates.   |
|-----------------------------------------------------------------------------------------------------|----------------------------------------------------------------------|
| [`fetch_location`](#ghir.fetch.fetch_location)(location, \*[, graphql, page_size]) | Yield normalized repo records for one owner login or `search:` spec. |
| [`fetch_repos`](#ghir.fetch.fetch_repos)(locations, \*[, exclude, ...])         | Yield repo records over all `locations`, skipping excluded repos.    |
| [`normalize_repo`](#ghir.fetch.normalize_repo)(node)                               | Flatten one GraphQL repository node into a JSON-friendly record.     |

### ghir.fetch.README_NAMES *= ('README.md', 'readme.md', 'README.rst', 'README', 'README.txt')*

README file names tried, in order, at the default branch’s root.

### ghir.fetch.expand_locations(locations, \*, owners=<function my_owners>)

Replace `"@me"` by the user’s owners; keep order, drop duplicates.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### ghir.fetch.fetch_location(location, \*, graphql=<function gh_graphql>, page_size=25)

Yield normalized repo records for one owner login or `search:` spec.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]

### ghir.fetch.fetch_repos(locations, \*, exclude=(), graphql=<function gh_graphql>, owners=<function my_owners>, on_error=None)

Yield repo records over all `locations`, skipping excluded repos.

A location whose fetch fails is passed to `on_error(location, error)` and
skipped, or, when `on_error` is None, the error propagates.

An owner pattern in `exclude` (`"Acme/*"`) also stops that owner from
being queried at all, so nothing of it is fetched.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]

### ghir.fetch.normalize_repo(node)

Flatten one GraphQL repository node into a JSON-friendly record.

```pycon
>>> normalize_repo({"nameWithOwner": "a/b", "name": "b",
...     "primaryLanguage": {"name": "Python"},
...     "repositoryTopics": {"nodes": [{"topic": {"name": "x"}}]},
...     "readme0": None, "readme1": {"text": "hi"}})["readme"]
'hi'
```

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)
