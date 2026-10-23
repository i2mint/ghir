# ghir.local

Which GitHub repos are cloned on this machine, and where.

Scans root directories a few levels deep for git checkouts and reads each one’s
`origin` remote, giving `{"owner/name": local_path}`. Plain file reads, no
`git` subprocess, so a scan of a few hundred checkouts takes well under a second.

### Module Attributes

| [`DFLT_MAX_DEPTH`](#ghir.local.DFLT_MAX_DEPTH)   | How many directory levels below each root to look for checkouts.   |
|-------------------------------------------------------------------|--------------------------------------------------------------------|

### Functions

| [`excluded_clones`](#ghir.local.excluded_clones)(clones, patterns, \*[, roots])   | Ids of `clones` whose path matches a pattern, absolute or root-relative.   |
|---------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------|
| [`local_clones`](#ghir.local.local_clones)(roots, \*[, max_depth])             | `{"owner/name" (lowercased): path}` for git checkouts under `roots`.       |
| [`origin_repo_id`](#ghir.local.origin_repo_id)(config_text)                      | The `owner/name` of the first GitHub remote in a `.git/config`.            |

### ghir.local.DFLT_MAX_DEPTH *= 3*

How many directory levels below each root to look for checkouts.

### ghir.local.excluded_clones(clones, patterns, , roots=())

Ids of `clones` whose path matches a pattern, absolute or root-relative.

```pycon
>>> excluded_clones({"o/a": "/p/q/a", "o/b": "/p/t/b"}, ["q/*"], roots=["/p"])
{'o/a'}
```

* **Return type:**
  [`set`](https://docs.python.org/3/builtins/stdtypes.html#set)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### ghir.local.local_clones(roots, , max_depth=3)

`{"owner/name" (lowercased): path}` for git checkouts under `roots`.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

### ghir.local.origin_repo_id(config_text)

The `owner/name` of the first GitHub remote in a `.git/config`.

```pycon
>>> origin_repo_id('[remote "origin"]\n\turl = git@github.com:i2mint/ir.git\n')
'i2mint/ir'
>>> origin_repo_id('url = https://github.com/thorwhalen/learny\n')
'thorwhalen/learny'
```

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`None`](https://docs.python.org/3/builtins/constants.html#None)
