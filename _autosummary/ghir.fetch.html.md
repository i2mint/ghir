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

| [`MIN_PAGE_SIZE`](#ghir.fetch.MIN_PAGE_SIZE)   | On a gateway error (README blobs make pages slow), the page size is halved down to this before the error is let through.   |
|------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------|
| [`README_NAMES`](#ghir.fetch.README_NAMES)    | README file names tried, in order, at the default branch's root.                                                           |

### Functions

| [`expand_locations`](#ghir.fetch.expand_locations)(locations, \*[, owners])          | Replace `"@me"` by the user's owners; keep order, drop duplicates.      |
|-----------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------|
| [`fetch_location`](#ghir.fetch.fetch_location)(location, \*[, graphql, page_size]) | Yield normalized repo records for one owner login or `search:` spec.    |
| [`fetch_repos`](#ghir.fetch.fetch_repos)(locations, \*[, exclude, ...])         | Yield repo records over all `locations`, skipping excluded repos.       |
| [`gh_api`](#ghir.fetch.gh_api)(path)                                       | `gh api <path>` (REST), JSON-decoded.                                   |
| [`gh_graphql`](#ghir.fetch.gh_graphql)(query, variables)                       | Run a GraphQL query through `gh api graphql` and return its `data`.     |
| [`is_excluded`](#ghir.fetch.is_excluded)(repo_id, exclude)                      | Whether `owner/name` matches any fnmatch pattern of `exclude`.          |
| [`my_owners`](#ghir.fetch.my_owners)(\*[, rest])                              | The authenticated user's login followed by their organizations' logins. |
| [`normalize_repo`](#ghir.fetch.normalize_repo)(node)                               | Flatten one GraphQL repository node into a JSON-friendly record.        |

### ghir.fetch.MIN_PAGE_SIZE *= 3*

On a gateway error (README blobs make pages slow), the page size is halved
down to this before the error is let through.

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

### ghir.fetch.gh_api(path)

`gh api <path>` (REST), JSON-decoded.

* **Return type:**
  [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

### ghir.fetch.gh_graphql(query, variables)

Run a GraphQL query through `gh api graphql` and return its `data`.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### ghir.fetch.is_excluded(repo_id, exclude)

Whether `owner/name` matches any fnmatch pattern of `exclude`.

```pycon
>>> is_excluded("Acme/x", ["acme/*"]), is_excluded("i2mint/x", ["acme/*"])
(True, False)
```

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### ghir.fetch.my_owners(\*, rest=<function gh_api>)

The authenticated user’s login followed by their organizations’ logins.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

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
