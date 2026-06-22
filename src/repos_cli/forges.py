"""Classify a repo's remote into a forge short name, and filter by forge."""

from collections.abc import Iterable, Sequence

from repos_cli.models import RepoInfo

# Ordered (host substring -> forge short name). Substring matching means
# self-hosted/enterprise hosts that contain the forge name (e.g.
# "github.acme.com") also classify correctly.
_HOST_SIGNATURES = (
    ("github", "github"),
    ("gitlab", "gitlab"),
    ("bitbucket", "bitbucket"),
    ("codeberg", "codeberg"),
    ("dev.azure.com", "ado"),
    ("visualstudio.com", "ado"),
    ("sr.ht", "sourcehut"),
    ("gitea", "gitea"),
)

# "local" is a pseudo-forge matching repos with no remote.
FORGES = tuple(dict.fromkeys(forge for _, forge in _HOST_SIGNATURES)) + ("local",)


def forge_of(remote: str) -> str | None:
    """Return the forge short name for a short ``host/path`` remote.

    ``"local"`` (no remote) maps to ``"local"``; an unrecognized host yields
    ``None``.
    """
    if not remote:
        return None
    if remote == "local":
        return "local"
    host = remote.split("/", 1)[0].lower()
    for signature, forge in _HOST_SIGNATURES:
        if signature in host:
            return forge
    return None


def filter_by_forge(repos: Sequence[RepoInfo], forges: Iterable[str]) -> list[RepoInfo]:
    """Keep only repos whose forge is in ``forges`` (empty ``forges`` keeps all)."""
    wanted = {f.lower() for f in forges}
    if not wanted:
        return list(repos)
    return [r for r in repos if forge_of(r.remote) in wanted]
