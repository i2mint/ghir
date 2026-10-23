"""Which GitHub repos are cloned on this machine, and where.

Scans root directories a few levels deep for git checkouts and reads each one's
``origin`` remote, giving ``{"owner/name": local_path}``. Plain file reads, no
``git`` subprocess, so a scan of a few hundred checkouts takes well under a second.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from pathlib import Path

#: How many directory levels below each root to look for checkouts.
DFLT_MAX_DEPTH = 3
_SKIP = {"node_modules", ".venv", "venv", "__pycache__", "site-packages", ".git"}
_GITHUB_REMOTE = re.compile(
    r"url\s*=\s*\S*github\.com[:/]([^/\s]+)/([^/\s]+?)(?:\.git)?/?\s*$", re.M
)


def origin_repo_id(config_text: str) -> str | None:
    """The ``owner/name`` of the first GitHub remote in a ``.git/config``.

    >>> origin_repo_id('[remote "origin"]\\n\\turl = git@github.com:i2mint/ir.git\\n')
    'i2mint/ir'
    >>> origin_repo_id('url = https://github.com/thorwhalen/learny\\n')
    'thorwhalen/learny'
    """
    m = _GITHUB_REMOTE.search(config_text)
    return f"{m.group(1)}/{m.group(2)}" if m else None


def local_clones(
    roots: Iterable[str | Path], *, max_depth: int = DFLT_MAX_DEPTH
) -> dict[str, str]:
    """``{"owner/name" (lowercased): path}`` for git checkouts under ``roots``."""
    found: dict[str, str] = {}

    def walk(d: Path, depth: int):
        cfg = d / ".git" / "config"
        if cfg.is_file():
            rid = origin_repo_id(cfg.read_text(errors="replace"))
            if rid:
                found.setdefault(rid.lower(), str(d))
        if depth >= max_depth:
            return
        try:
            subdirs = [e for e in os.scandir(d) if e.is_dir(follow_symlinks=False)]
        except OSError:
            return
        for e in subdirs:
            if e.name not in _SKIP and not e.name.startswith("."):
                walk(Path(e.path), depth + 1)

    for root in roots:
        walk(Path(root).expanduser(), 0)
    return found
