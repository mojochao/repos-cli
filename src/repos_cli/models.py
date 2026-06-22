"""Data structures shared across the package."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RepoInfo:
    """A single git repository's summary, one table row.

    ``branch`` holds the current branch name, or a short SHA when HEAD is
    detached. ``committed_at`` (the last commit's Unix timestamp) and ``author``
    come from the last commit and are ``None`` for a repo with no commits yet.
    Display forms (days-since, datetime stamp) are derived at render time.
    ``remote`` is the remote in short ``host/path`` form (protocol, credentials,
    port, and ``.git`` suffix stripped), or the literal ``"local"`` when the
    repo has no remote configured.
    """

    name: str
    branch: str
    dirty: bool
    committed_at: int | None
    author: str | None
    remote: str
    path: str
