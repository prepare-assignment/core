import re
from typing import Dict, Final, List, Optional, Tuple, cast

from git import Git
from packaging.version import InvalidVersion, Version

from prepare_assignment.data.constants import CONFIG
from prepare_assignment.data.task_properties import TaskProperties

COMMIT_HASH_RE: Final[re.Pattern] = re.compile(r'^[0-9a-f]{40}$')


def get_git_url(props: TaskProperties) -> str:
    if CONFIG.core.git_mode == "https":
        return f"https://github.com/{props.organization}/{props.name}.git"
    return f"git@github.com:{props.organization}/{props.name}.git"


def get_web_url(props: TaskProperties) -> str:
    return f"https://github.com/{props.organization}/{props.name}"


def list_remote_tags(git_url: str) -> Dict[str, str]:
    """
    List the tags of a remote repository

    :param git_url: url of the repository
    :return: mapping from tag name to the commit it points to (annotated tags are peeled)
    """
    raw = cast(str, Git().ls_remote("--tags", git_url))
    tags: Dict[str, str] = {}
    peeled: Dict[str, str] = {}
    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) != 2 or not parts[1].startswith("refs/tags/"):
            continue
        sha, ref = parts
        name = ref[len("refs/tags/"):]
        if name.endswith("^{}"):
            peeled[name[:-3]] = sha
        else:
            tags[name] = sha
    return {name: peeled.get(name, sha) for name, sha in tags.items()}


def remote_ref(git_url: str, ref: str = "HEAD") -> Optional[str]:
    """
    Get the commit a remote ref (branch or HEAD) points to

    :return: commit hash, or None if the ref doesn't exist
    """
    raw = cast(str, Git().ls_remote(git_url, ref))
    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) == 2 and parts[1] in (ref, f"refs/heads/{ref}"):
            return parts[0]
    return None


def _as_version(tag: str) -> Optional[Version]:
    try:
        return Version(tag)
    except InvalidVersion:
        return None


def highest_tag(tags: List[str], prefix: Optional[str] = None) -> Optional[str]:
    """
    Get the highest (semver) tag, optionally only considering tags that start with prefix
    """
    candidates: List[Tuple[Version, str]] = []
    for tag in tags:
        if prefix is not None and not tag.startswith(prefix):
            continue
        version = _as_version(tag)
        if version is not None:
            candidates.append((version, tag))
    if not candidates:
        return None
    return max(candidates, key=lambda x: x[0])[1]


def resolve_version_from_tags(tags: List[str], version: str) -> Optional[str]:
    """
    Resolve a version string to a concrete git ref, given the tags of the repository.

    - "main"    → "main" (latest commit on main branch)
    - "latest"  → highest semver tag; None if no tags exist (falls back to default branch)
    - "v1.0.0"  → exact tag if it exists, otherwise treated as prefix
    - "v1"      → highest semver tag whose name starts with "v1"
    - 40-char hex → passed through as-is (commit hash, handled separately)
    - other     → passed through as-is
    """
    if version == "main" or COMMIT_HASH_RE.match(version):
        return version
    if version == "latest":
        return highest_tag(tags)
    if version in tags:
        return version
    prefixed = highest_tag(tags, prefix=version)
    if prefixed is not None:
        return prefixed
    # Fallback (branch name, partial ref, etc.)
    return version


def resolve_version(git_url: str, version: str) -> Optional[str]:
    """
    Resolve a version string to a concrete git ref by inspecting remote tags, see resolve_version_from_tags
    """
    if version == "main" or COMMIT_HASH_RE.match(version):
        return version
    return resolve_version_from_tags(list(list_remote_tags(git_url).keys()), version)


def is_fixed_version(git_url: str, version: str) -> bool:
    """
    A version is fixed if it is a commit hash or an exact tag, all others (latest, main, v1, branches) can move
    """
    if COMMIT_HASH_RE.match(version):
        return True
    if version in ("latest", "main"):
        return False
    return version in list_remote_tags(git_url)
