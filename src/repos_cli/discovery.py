"""Find git repositories underneath one or more parent directories."""

import os
from collections.abc import Iterable


def _is_repo(path: str) -> bool:
    # A working tree has a ``.git`` directory; submodules and worktrees use a
    # ``.git`` file. ``exists`` covers both.
    return os.path.exists(os.path.join(path, ".git"))


def find_repos(roots: Iterable[str]) -> list[str]:
    """Return real paths of every git repo found under ``roots``.

    Each tree is walked top-down. When a repo is found its subtree is pruned,
    so a repo nested inside another repo's working tree is not reported twice.
    Results are de-duplicated by real path, preserving first-seen order. Paths
    that do not exist are skipped silently.
    """
    found: list[str] = []
    seen: set[str] = set()
    for root in roots:
        for dirpath, dirnames, _ in os.walk(root):
            if _is_repo(dirpath):
                real = os.path.realpath(dirpath)
                if real not in seen:
                    seen.add(real)
                    found.append(real)
                dirnames[:] = []  # prune: do not descend into a repo
    return found
