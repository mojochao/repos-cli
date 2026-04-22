# repos-cli

I organize my git repositories in a structure way under a root directory.

```text
REPOS_ROOT/
REPOS_ROOT/$FORGE
REPOS_ROOT/$FORGE/$USER
REPOS_ROOT/$FORGE/$USER/$REPO
```

I use several forges, including:

- github.com
- gitlab.com
- bitbucket.org
- codeberg.org
- git.savannah.gnu.org

I need a way to:

1. quickly add a repo by URL
   - parse out the path components
   - make parent directories as needed
   - clone repo in its parent directory
2. list added repos
   - with no arg, list all repos
   - with arg containing just the forge path, list all repos under that forge directory
   - with arg containing just the forge/user path, list all repos under that specific user directory under that forge directory
   - optionally add git status info such as branch name, dirty status, etc

This repository provides a `repos` CLI that provides this functionality.

Run `repos --help` to read the top-level docs.

Examples of its use include:

``` text
repos add [-r, --root PATH] [-d, --depth] URL
repos list [-r, --root PATH] [-s, --status] [--json] QUERY
```

The `REPO` argument is simply a relative path from the repo root dir separated
by the usual `/` path separator on macOS and Linux.

- zero path components indicates all forges, users, and repos
- one path component indicate all users and repos for the specified forge
- two path components indicate all repos for the specified forge/user
- three path components indicate the specific forge/user/repo

If I ever decide to run it on Windows, I will still use `/` as the canonical
form, as I find the `\` delimiter ugly.

Note that the repo root can also be specified as an env var REPOS_ROOT.
If defined, it will be the default value of the -r,--root option.

Note also that the output for the `list` command should use colors and icons
its output in a pleasing manner for human consumption, when the `--json`
flag is not provided.

Golang has several libraries for command line parsing. I prefer `urfave/cli/v3`
package.

## Installation

Install the latest version with:

```sh
go install github.com/mojochao/repos-cli@latest
```

## License

This project is licensed under the [MIT License](LICENSE).
