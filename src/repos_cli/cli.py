"""Command-line entry point: parse args, discover repos, print the table."""

import argparse
import os
import sys
from collections.abc import Mapping, Sequence

from repos_cli.discovery import find_repos
from repos_cli.forges import FORGES, filter_by_forge
from repos_cli.git import get_info
from repos_cli.render import render
from repos_cli.sorting import SORT_COLUMNS, sort_repos


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repos",
        description="Display a table of git repos found under one or more parent directories.",
    )
    parser.add_argument(
        "parents",
        nargs="+",
        metavar="PARENT",
        help="parent directory to search for git repositories",
    )
    parser.add_argument(
        "--path",
        action="store_true",
        help="include the full repository path as a column",
    )
    parser.add_argument(
        "--time",
        action="store_true",
        help="include the last-commit datetime stamp as a column after 'Updated'",
    )
    parser.add_argument(
        "--remote",
        action="store_true",
        help="include the remote URL (or 'local') as a column",
    )
    parser.add_argument(
        "--forge",
        action="append",
        metavar="FORGE",
        help="only show repos on this forge (repeatable); choose from: " + ", ".join(FORGES),
    )
    parser.add_argument(
        "--sort",
        metavar="COLUMNS",
        help="comma-separated column(s) to sort by (default: name); valid: " + ", ".join(SORT_COLUMNS),
    )
    parser.add_argument(
        "--desc",
        action="store_true",
        help="reverse the sort order",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="disable color (also auto-disabled when not a TTY or when NO_COLOR is set)",
    )
    return parser


def should_use_color(no_color: bool, isatty: bool, env: Mapping[str, str]) -> bool:
    """Decide whether to emit ANSI color, honoring the ``NO_COLOR`` convention."""
    if no_color or not isatty:
        return False
    return "NO_COLOR" not in env


def _split_columns(value: str | None) -> list[str]:
    if not value:
        return []
    return [c.strip().lower() for c in value.split(",") if c.strip()]


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    sort_columns = _split_columns(args.sort)
    unknown = [c for c in sort_columns if c not in SORT_COLUMNS]
    if unknown:
        parser.error(
            f"unknown sort column(s): {', '.join(unknown)} (valid: {', '.join(SORT_COLUMNS)})"
        )

    forges = [f.lower() for f in (args.forge or [])]
    unknown_forges = [f for f in forges if f not in FORGES]
    if unknown_forges:
        parser.error(
            f"unknown forge(s): {', '.join(unknown_forges)} (valid: {', '.join(FORGES)})"
        )

    missing = [p for p in args.parents if not os.path.isdir(p)]
    for path in missing:
        print(f"repos: {path}: not a directory", file=sys.stderr)
    valid = [p for p in args.parents if os.path.isdir(p)]

    repos = filter_by_forge(
        [get_info(path) for path in find_repos(valid)],
        forges,
    )
    repos = sort_repos(repos, sort_columns, desc=args.desc)
    if repos:
        use_color = should_use_color(args.no_color, sys.stdout.isatty(), os.environ)
        print(render(
            repos,
            show_path=args.path,
            show_time=args.time,
            show_remote=args.remote,
            use_color=use_color,
        ))
    else:
        print("No repositories found.", file=sys.stderr)

    return 1 if missing else 0
