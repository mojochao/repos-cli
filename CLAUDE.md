# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`repos-cli` prints a table of git repositories found under one or more parent directories. Always-on columns: name, status (branch/ref + `*` dirty marker), Updated (days since last commit), author. Optional columns (each behind a flag): `--time` adds a datetime stamp after Updated; `--remote` adds the remote in short `host/path` form (or `local`); `--path` adds the full path. Rows can be filtered by forge (`--forge`, repeatable) and sorted (`--sort`/`--desc`). `README.md` documents the user-facing contract.

## Commands

Managed with `uv` (Python 3.14, pinned in `.python-version`).

- Sync env / install: `uv sync`
- Run the CLI: `uv run repos <parent-dir>...` (or `uv run python -m repos_cli <parent-dir>...`)
- Run all tests: `uv run python -m unittest discover -s tests`
- Run one module: `uv run python -m unittest tests.test_git`
- Run one test: `uv run python -m unittest tests.test_git.GitInfoTest.test_clean_repo_is_not_dirty`

There is no separate lint/format tool configured. The `[tool.pyright]` block in `pyproject.toml` only points the type checker at the `src` layout and Python 3.14.

## Architecture

`src/repos_cli/` is a small package; the `repos` console script maps to `repos_cli.cli:main`. The data flows through four single-purpose modules:

`cli.py` (argparse + orchestration) → `discovery.find_repos(parents)` → `git.get_info(path)` → `render.render(rows)` → stdout.

- **`models.py`** — `RepoInfo` frozen dataclass, the one row shape shared by `git` (producer) and `render` (consumer). Keeping it here keeps `render` independent of `git`.
- **`discovery.py`** — recursive `os.walk`, treats any dir containing `.git` as a repo, then **prunes** (does not descend into a repo). Results are de-duped by real path. A repo nested inside another repo's working tree is therefore not listed.
- **`git.py`** — shells out to the `git` binary via `subprocess` (the stdlib-native route; there is no stdlib git). Every query is **best-effort**: a failing command degrades to a default (`branch="(unknown)"`, no metadata) instead of raising, so one odd repo never aborts the whole table.
- **`render.py`** — builds a `rich` `Table` and returns it as a string (so `cli` stays a thin `print(render(...))`). Color is driven by the explicit `use_color` flag passed in, **not** rich's own terminal detection — the color decision lives in `cli.should_use_color`, and a fixed-large console width keeps cells from wrapping/truncating.
- **`sorting.py`** — pure: maps column names (`name`, `status`, `updated`/`time`, `author`, `remote`, `path`) to key functions and sorts a `RepoInfo` list. `--desc` is a global `reverse`. Nullable fields use a `(is_missing, value)` key so missing data sorts last. `SORT_COLUMNS` is the validation/help source of truth.
- **`forges.py`** — pure: `forge_of(remote)` classifies a short remote into a forge short name by host substring (`local` is a pseudo-forge for no-remote; unknown host → `None`); `filter_by_forge` keeps matching repos. `FORGES` is the validation/help source of truth.
- **`cli.py`** — validates parents (missing → stderr warning, exit 1), sort columns, and forge names (unknown → `parser.error`, exit 2); pipeline is discover → `get_info` → `filter_by_forge` → `sort_repos` → render. Color decided via `should_use_color`.

## Conventions and deliberate decisions

These are intentional; preserve them unless asked to change:

- **Lean dependencies** — the only runtime dep is `rich` (rendering). **Git access stays on `subprocess`** by deliberate choice: GitPython merely wraps the `git` binary (a dependency that doesn't remove the binary requirement), and pygit2/dulwich are overkill for three cheap reads. Do not add a git library. If git speed ever matters at scale, collapse calls (`git status --porcelain=v2 --branch`) and/or parallelize — don't reach for a dependency.
- **Python 3.14** — use native `X | None` / builtin generics; do **not** add `from __future__ import annotations`.
- **"Dirty" means tracked changes only** — untracked files do not mark a repo dirty (`git status --porcelain --untracked-files=no`). This is why this repo can show clean while holding untracked files.
- **Color is opt-out and TTY-aware** — auto-disabled when stdout is not a TTY or `NO_COLOR` is set; `--no-color` forces it off.

## Testing

TDD with the stdlib `unittest` (no pytest). Tests live in `tests/` as a package. The `git`/`cli` layers are tested against **real** temporary repos created with `git init` (so the `git` binary must be on PATH); `discovery` uses fake `.git` dirs; `render` is tested as a pure function. New behavior gets a failing test first.
