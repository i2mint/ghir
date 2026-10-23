"""Settings for ghir: where the cache lives and which repos are in scope.

All settings have working defaults and can be overridden, in increasing order of
precedence, by a JSON file (``~/.config/ghir/config.json``, or ``$GHIR_CONFIG``)
and by keyword arguments to the functions that read them. The file is the place
for machine-specific choices (extra owners, owners or repos never to fetch):

.. code-block:: json

    {"locations": ["@me", "otosense"],
     "exclude": ["SomeClientOrg/*", "myorg/private-notes"]}

``"@me"`` expands to the authenticated GitHub user plus every organization they
belong to (see :func:`ghir.fetch.my_owners`).
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def _xdg(var: str, fallback: str) -> Path:
    return Path(os.environ.get(var) or Path.home() / fallback)


#: Where fetched repo records are cached (one JSON file per ``owner/name``).
DFLT_CACHE_DIR = _xdg("XDG_DATA_HOME", ".local/share") / "ghir" / "repos"

#: The optional user settings file.
DFLT_CONFIG_PATH = _xdg("XDG_CONFIG_HOME", ".config") / "ghir" / "config.json"

#: The ir corpus name the default records are registered under.
DFLT_CORPUS_NAME = "gh_repos"

DFLT_SETTINGS: Mapping[str, Any] = {
    # Owners (user or org logins) and/or "search:<github search query>" specs.
    "locations": ["@me"],
    # fnmatch patterns over "owner/name"; matching repos are never fetched.
    "exclude": [],
    # Name of the extractor (see ghir.extract.extractors) turning a repo into text.
    "extract": "description_and_readme",
    # Root directories scanned (a few levels deep) for local clones.
    "local_roots": [os.environ.get("PP") or str(Path.home())],
    "cache_dir": str(DFLT_CACHE_DIR),
    "corpus_name": DFLT_CORPUS_NAME,
}


def settings(path: str | Path | None = None, **overrides) -> dict:
    """The effective settings: defaults, then the config file, then ``overrides``.

    >>> s = settings(path="/nonexistent/ghir.json", exclude=["acme/*"])
    >>> s["exclude"], s["locations"]
    (['acme/*'], ['@me'])
    """
    path = Path(path or os.environ.get("GHIR_CONFIG") or DFLT_CONFIG_PATH)
    from_file = json.loads(path.read_text()) if path.is_file() else {}
    unknown = set(from_file) - set(DFLT_SETTINGS)
    if unknown:
        raise ValueError(
            f"Unknown ghir setting(s) {sorted(unknown)} in {path}; "
            f"known: {sorted(DFLT_SETTINGS)}"
        )
    given = {k: v for k, v in overrides.items() if v is not None}
    return {**DFLT_SETTINGS, **from_file, **given}
