# ghir.owners

Owner logins -> repo records, stdlib only (no `ir`, no `dol`).

The reusable half of [`ghir.fetch`](ghir.fetch.html.md#module-ghir.fetch): a GraphQL transport seam (`graphql=`,
a callable `(query, variables) -> dict`; [`gh_graphql()`](#ghir.owners.gh_graphql) shells out to the
`gh` CLI, [`urllib_graphql()`](#ghir.owners.urllib_graphql) needs only a token), `"@me"` expansion,
fnmatch exclusion and cursor pagination that backs off the page size on gateway
errors. What a record *contains* is a seam too: `fields` is the GraphQL
selection and `normalize` flattens a node, so ghir asks for README blobs while
another collector asks for permissions and fork counts.

```pycon
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
```

### Module Attributes

| [`MIN_PAGE_SIZE`](#ghir.owners.MIN_PAGE_SIZE)   | On a gateway error, the page size is halved down to this before the error is let through.   |
|------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| [`DFLT_FIELDS`](#ghir.owners.DFLT_FIELDS)     | The least a repo listing needs; pass a richer `fields=` selection to ask for more.          |

### Functions

| [`expand_owners`](#ghir.owners.expand_owners)(owners, \*, me)                  | Replace `"@me"` by the user's owners; keep order, drop case-insensitive duplicates.   |
|-------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------|
| [`gh_api`](#ghir.owners.gh_api)(path)                                   | `gh api <path>` (REST), JSON-decoded.                                                 |
| [`gh_graphql`](#ghir.owners.gh_graphql)(query, variables)                   | Run a GraphQL query through `gh api graphql` and return its `data`.                   |
| [`is_excluded`](#ghir.owners.is_excluded)(repo_id, exclude)                  | Whether `owner/name` matches any fnmatch pattern of `exclude`.                        |
| [`list_repos`](#ghir.owners.list_repos)(owners, \*[, graphql, fields, ...]) | Yield a record per repo over `owners` (`"@me"` expanded), minus `exclude`.            |
| [`my_owners`](#ghir.owners.my_owners)(\*[, rest])                          | The authenticated user's login followed by their organizations' logins.               |
| [`owner_nodes`](#ghir.owners.owner_nodes)(owner, \*[, graphql, fields, ...]) | Yield the raw GraphQL nodes of every repo owned by `owner` (`fields` selects them).   |
| [`urllib_graphql`](#ghir.owners.urllib_graphql)([token, url, timeout])          | A GraphQL transport over `urllib` and a token (default `$GITHUB_TOKEN`/`$GH_TOKEN`).  |

### ghir.owners.DFLT_FIELDS *= 'nameWithOwner name description url isFork isArchived isPrivate'*

The least a repo listing needs; pass a richer `fields=` selection to ask for more.

### ghir.owners.MIN_PAGE_SIZE *= 3*

On a gateway error, the page size is halved down to this before the error is let through.

### ghir.owners.expand_owners(owners, , me)

Replace `"@me"` by the user’s owners; keep order, drop case-insensitive duplicates.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### ghir.owners.gh_api(path)

`gh api <path>` (REST), JSON-decoded.

* **Return type:**
  [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)

### ghir.owners.gh_graphql(query, variables)

Run a GraphQL query through `gh api graphql` and return its `data`.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

### ghir.owners.is_excluded(repo_id, exclude)

Whether `owner/name` matches any fnmatch pattern of `exclude`.

```pycon
>>> is_excluded("Acme/x", ["acme/*"]), is_excluded("i2mint/x", ["acme/*"])
(True, False)
```

* **Return type:**
  [`bool`](https://docs.python.org/3/builtins/functions.html#bool)

### ghir.owners.list_repos(owners, \*, graphql=<function gh_graphql>, fields='nameWithOwner name description url isFork isArchived isPrivate', normalize=None, exclude=(), me=<function my_owners>, page_size=25, on_error=None)

Yield a record per repo over `owners` (`"@me"` expanded), minus `exclude`.

`normalize` maps a node to the record (default: the node itself). An owner
pattern in `exclude` (`"acme/*"`) also stops that owner being queried. An
owner whose listing fails goes to `on_error(owner, error)` and is skipped,
or, when `on_error` is None, the error propagates.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### ghir.owners.my_owners(\*, rest=<function gh_api>)

The authenticated user’s login followed by their organizations’ logins.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### ghir.owners.owner_nodes(owner, \*, graphql=<function gh_graphql>, fields='nameWithOwner name description url isFork isArchived isPrivate', page_size=25)

Yield the raw GraphQL nodes of every repo owned by `owner` (`fields` selects them).

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterator)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]

### ghir.owners.urllib_graphql(token=None, , url='https://api.github.com/graphql', timeout=60)

A GraphQL transport over `urllib` and a token (default `$GITHUB_TOKEN`/`$GH_TOKEN`).

For environments without the `gh` CLI (a GitHub Action, a container).

* **Return type:**
  [`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Mapping`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]], [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]
