"""Read repository summaries by shelling out to the ``git`` binary.

The standard library has no git support, so ``subprocess`` is the stdlib-native
way to talk to git. Each query is best-effort: a failing command degrades to a
sensible default rather than raising, so one odd repo never aborts the table.
"""

import os
import subprocess

from repos_cli.models import RepoInfo

# Committer date as a Unix timestamp, NUL-separated from the author name so
# neither field can be confused with the other regardless of its contents.
# Display forms are derived later, in the render layer.
_LOG_FORMAT = "%ct%x00%an"


def _git(repo_path: str, *args: str) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", "-C", repo_path, *args],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout.strip()


def _branch(repo_path: str) -> str:
    # On a normal checkout (including a repo with no commits yet) this returns
    # the branch name. It fails when HEAD is detached.
    code, out = _git(repo_path, "symbolic-ref", "--short", "-q", "HEAD")
    if code == 0 and out:
        return out
    code, out = _git(repo_path, "rev-parse", "--short", "HEAD")
    if code == 0 and out:
        return out
    return "(unknown)"


def _is_dirty(repo_path: str) -> bool:
    # Tracked changes only: untracked files do not count as dirty.
    _, out = _git(repo_path, "status", "--porcelain", "--untracked-files=no")
    return bool(out)


def short_remote(url: str) -> str:
    """Reduce a git remote URL to ``host/path`` form.

    Drops the protocol, any user/credentials, a port, and a trailing ``.git``.
    Handles scp-style (``git@host:path``), ``scheme://`` URLs, and leaves
    anything unrecognised (e.g. a local path or the ``"local"`` sentinel)
    essentially untouched apart from the ``.git`` suffix.
    """
    text = url.strip()
    if "://" in text:
        text = text.split("://", 1)[1]  # drop scheme
        text = text.split("@", 1)[-1]  # drop any userinfo
        host, slash, path = text.partition("/")
        host = host.split(":", 1)[0]  # drop any port
        text = f"{host}/{path}" if slash else host
    else:
        head = text.split("/", 1)[0]
        if "@" in head:
            text = text.split("@", 1)[-1]  # drop scp-style user
            head = text.split("/", 1)[0]
        if ":" in head:  # scp-style host:path
            host, _, path = text.partition(":")
            text = f"{host}/{path}" if path else host
    text = text.rstrip("/")
    if text.endswith(".git"):
        text = text[: -len(".git")]
    return text


def _remote(repo_path: str) -> str:
    code, out = _git(repo_path, "remote")
    if code != 0 or not out:
        return "local"
    names = out.splitlines()
    name = "origin" if "origin" in names else names[0]
    code, url = _git(repo_path, "remote", "get-url", name)
    if code != 0 or not url:
        return "local"
    return short_remote(url)


def _last_commit(repo_path: str) -> tuple[int | None, str | None]:
    code, out = _git(repo_path, "log", "-1", f"--format={_LOG_FORMAT}")
    if code != 0 or not out:
        return None, None
    timestamp, _, author = out.partition("\x00")
    committed_at = int(timestamp) if timestamp.isdigit() else None
    return committed_at, author or None


def get_info(repo_path: str) -> RepoInfo:
    """Summarize the git repo at ``repo_path`` into a :class:`RepoInfo`."""
    committed_at, author = _last_commit(repo_path)
    return RepoInfo(
        name=os.path.basename(repo_path),
        branch=_branch(repo_path),
        dirty=_is_dirty(repo_path),
        committed_at=committed_at,
        author=author,
        remote=_remote(repo_path),
        path=repo_path,
    )
