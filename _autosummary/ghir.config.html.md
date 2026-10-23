# ghir.config

Settings for ghir: where the cache lives and which repos are in scope.

All settings have working defaults and can be overridden, in increasing order of
precedence, by a JSON file (`~/.config/ghir/config.json`, or `$GHIR_CONFIG`)
and by keyword arguments to the functions that read them. The file is the place
for machine-specific choices (extra owners, owners or repos never to fetch):

```json
{"locations": ["@me", "otosense"],
 "exclude": ["SomeClientOrg/*", "myorg/private-notes"]}
```

`"@me"` expands to the authenticated GitHub user plus every organization they
belong to (see [`ghir.fetch.my_owners()`](ghir.fetch.html.md#ghir.fetch.my_owners)).

### Module Attributes

| [`DFLT_CACHE_DIR`](#ghir.config.DFLT_CACHE_DIR)   | Where fetched repo records are cached (one JSON file per `owner/name`).   |
|-------------------------------------------------------------------|---------------------------------------------------------------------------|
| [`DFLT_CONFIG_PATH`](#ghir.config.DFLT_CONFIG_PATH) | The optional user settings file.                                          |
| [`DFLT_CORPUS_NAME`](#ghir.config.DFLT_CORPUS_NAME) | The ir corpus name the default records are registered under.              |

### Functions

| [`settings`](#ghir.config.settings)([path])   | The effective settings: defaults, then the config file, then `overrides`.   |
|---------------------------------------------------------------------|-----------------------------------------------------------------------------|

### ghir.config.DFLT_CACHE_DIR *= PosixPath('/home/runner/.local/share/ghir/repos')*

Where fetched repo records are cached (one JSON file per `owner/name`).

### ghir.config.DFLT_CONFIG_PATH *= PosixPath('/home/runner/.config/ghir/config.json')*

The optional user settings file.

### ghir.config.DFLT_CORPUS_NAME *= 'gh_repos'*

The ir corpus name the default records are registered under.

### ghir.config.settings(path=None, \*\*overrides)

The effective settings: defaults, then the config file, then `overrides`.

```pycon
>>> s = settings(path="/nonexistent/ghir.json", exclude=["acme/*"])
>>> s["exclude"], s["locations"]
(['acme/*'], ['@me'])
```

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)
