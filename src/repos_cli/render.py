"""Render :class:`RepoInfo` rows into a table using rich.

``render`` returns the table as a string so the CLI stays a thin
``print(render(...))``. Color is driven by the explicit ``use_color`` flag
(decided by the CLI), not by rich's own terminal detection, which keeps the
color policy in one place and the output reproducible in tests. The current
time is likewise injected via ``now`` so the days-since column is testable.
"""

import time
from collections.abc import Sequence
from datetime import datetime

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from repos_cli.models import RepoInfo

_DASH = "—"
_SECONDS_PER_DAY = 86_400

# A width wide enough that rich never wraps or truncates a cell; with a
# non-expanding table this only grants headroom, it does not pad the output.
_MAX_WIDTH = 10_000


def _status_cell(repo: RepoInfo) -> Text:
    text = Text(repo.branch)
    if repo.dirty:
        text.append(" *")
        text.stylize("red")
    return text


def _days_since(committed_at: int | None, now: float) -> str:
    if committed_at is None:
        return _DASH
    days = max(0, int((now - committed_at) // _SECONDS_PER_DAY))
    return f"{days}d"


def _stamp(committed_at: int | None) -> str:
    if committed_at is None:
        return _DASH
    return datetime.fromtimestamp(committed_at).strftime("%Y-%m-%d %H:%M")


def render(
    rows: Sequence[RepoInfo],
    *,
    show_path: bool = False,
    show_time: bool = False,
    show_remote: bool = False,
    use_color: bool = False,
    now: float | None = None,
) -> str:
    """Return the repo table as a string (header rule plus one line per repo)."""
    if now is None:
        now = time.time()

    table = Table(box=box.SIMPLE_HEAD, pad_edge=False, show_edge=False, expand=False)
    table.add_column("Name")
    table.add_column("Status")
    table.add_column("Updated")
    if show_time:
        table.add_column("Time")
    table.add_column("Author")
    if show_remote:
        table.add_column("Remote")
    if show_path:
        table.add_column("Path", style="dim")

    for repo in rows:
        cells: list[object] = [
            repo.name,
            _status_cell(repo),
            _days_since(repo.committed_at, now),
        ]
        if show_time:
            cells.append(_stamp(repo.committed_at))
        cells.append(repo.author or _DASH)
        if show_remote:
            cells.append(repo.remote)
        if show_path:
            cells.append(repo.path)
        table.add_row(*cells)

    console = Console(
        width=_MAX_WIDTH,
        force_terminal=use_color or None,
        no_color=not use_color,
    )
    with console.capture() as capture:
        console.print(table)
    return capture.get().rstrip("\n")
