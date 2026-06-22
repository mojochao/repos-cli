# repos-cli

Display a table of git repositories found underneath one or more parent
directories. It recursively searches each parent directory you pass and prints
one row per repo.

## Usage

```
repos PARENT [PARENT ...] [--forge FORGE]... [--sort COLUMNS] [--desc] [--time] [--remote] [--path] [--no-color]
```

Run without installing via `uv`:

```
uv run repos ~/code ~/work
```

### Columns

| Column   | Contents                                                            |
|----------|---------------------------------------------------------------------|
| Name     | repo directory name                                                 |
| Status   | current branch (or short SHA if detached); a `*` marks tracked changes |
| Updated  | days since the last commit (e.g. `10d`), or `—` if there are no commits |
| Author   | last commit's author, or `—`                                        |

### Filtering by forge

`--forge` (repeatable) limits the table to repos hosted on the named forge(s).
Forges are detected from the remote host, so this works whether or not the
`Remote` column is shown.

```
repos ~/code --forge github                 # only GitHub repos
repos ~/code --forge github --forge gitlab  # GitHub or GitLab repos
repos ~/code --forge local                  # only repos with no remote
```

Recognized forges: `github`, `gitlab`, `bitbucket`, `codeberg`, `ado`
(Azure DevOps), `sourcehut`, `gitea`, and `local` (no remote). Detection is by
host substring, so enterprise/self-hosted hosts containing the forge name (e.g.
`github.acme.com`) are matched too.

### Sorting

Rows are sorted by `name` by default. Use `--sort` with one or more
comma-separated column names to change that, and `--desc` to reverse the order.

```
repos ~/code --sort author,name      # by author, ties broken by name
repos ~/code --sort updated          # most recently committed first
repos ~/code --sort updated --desc   # oldest first
```

Valid sort columns: `name`, `status` (branch), `updated`/`time` (commit
timestamp, most recently updated first), `author`, `remote`, `path`. A column
can be sorted on even when it is not displayed.

### Flags

- `--forge FORGE` — only show repos on this forge; repeatable (union). `local` selects repos with no remote.
- `--sort COLUMNS` — comma-separated column(s) to sort by (default: `name`).
- `--desc` — reverse the sort order.
- `--time` — add a `Time` column (last-commit datetime stamp) immediately after `Updated`.
- `--remote` — add a `Remote` column showing the remote in short `host/path` form (e.g. `github.com/acme/widgets`), prefers `origin`; `local` if no remote is configured. Added after `Author`.
- `--path` — add a `Path` column with the repo's full path.
- `--no-color` — disable color. Color is also auto-disabled when output is not a TTY or when `NO_COLOR` is set.

## Notes

- A repository nested inside another repository's working tree is not listed
  separately; discovery stops descending once it finds a repo.
- "Dirty" counts tracked changes only — untracked files do not mark a repo dirty.
