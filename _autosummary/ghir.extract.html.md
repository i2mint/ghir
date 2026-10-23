# ghir.extract

Extraction: what text each cached repo contributes to the search.

An extractor is a function `record -> str`. `extractors` names the
built-in ones; any callable works wherever an extractor is accepted. The text
returned is what gets indexed and ranked, so it decides what a query can match.

### Module Attributes

| [`DFLT_README_CHARS`](#ghir.extract.DFLT_README_CHARS)   | README characters kept by the default extractor (READMEs can be huge, and their opening says what the repo is).   |
|----------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------|

### Functions

| [`description`](#ghir.extract.description)(rec)                                | Name, description and topics.                                         |
|--------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------|
| [`description_and_readme`](#ghir.extract.description_and_readme)(rec, \*[, readme_chars]) | Name, description, topics, and the start of the README (the default). |
| [`resolve_extractor`](#ghir.extract.resolve_extractor)(extract)                      | An extractor from its name in `extractors`, or a callable as is.      |

### ghir.extract.DFLT_README_CHARS *= 6000*

README characters kept by the default extractor (READMEs can be huge, and
their opening says what the repo is).

### ghir.extract.description(rec)

Name, description and topics.

```pycon
>>> description({"name": "learny", "description": "Learner models",
...              "topics": ["education"]})
'learny\nLearner models\ntopics: education'
```

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### ghir.extract.description_and_readme(rec, , readme_chars=6000)

Name, description, topics, and the start of the README (the default).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

### ghir.extract.resolve_extractor(extract)

An extractor from its name in `extractors`, or a callable as is.

* **Return type:**
  [`Callable`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Callable)[[[`Mapping`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Mapping)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]], [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]
