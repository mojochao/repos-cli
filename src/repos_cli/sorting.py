"""Sort :class:`RepoInfo` rows by one or more named columns."""

from collections.abc import Sequence

from repos_cli.models import RepoInfo

# Maps a sortable column name to a key function over RepoInfo. Nullable fields
# return a ``(is_missing, value)`` tuple so missing data sorts last in ascending
# order. ``updated``/``time`` sort by commit timestamp but negated, so the
# default (ascending) order is most-recently-updated first.
_KEYS = {
    "name": lambda r: r.name.lower(),
    "status": lambda r: r.branch.lower(),
    "updated": lambda r: (r.committed_at is None, -(r.committed_at or 0)),
    "time": lambda r: (r.committed_at is None, -(r.committed_at or 0)),
    "author": lambda r: (r.author is None, (r.author or "").lower()),
    "remote": lambda r: r.remote.lower(),
    "path": lambda r: r.path.lower(),
}

SORT_COLUMNS = tuple(_KEYS)
DEFAULT_SORT = "name"


def sort_repos(
    repos: Sequence[RepoInfo],
    columns: Sequence[str],
    *,
    desc: bool = False,
) -> list[RepoInfo]:
    """Return ``repos`` sorted by the named ``columns`` (defaults to name).

    ``--desc`` reverses the whole ordering. Raises ``ValueError`` if any column
    name is not in :data:`SORT_COLUMNS`.
    """
    columns = list(columns) or [DEFAULT_SORT]
    unknown = [c for c in columns if c not in _KEYS]
    if unknown:
        raise ValueError(
            f"unknown sort column(s): {', '.join(unknown)} (valid: {', '.join(SORT_COLUMNS)})"
        )
    keys = [_KEYS[c] for c in columns]
    return sorted(repos, key=lambda r: tuple(key(r) for key in keys), reverse=desc)
