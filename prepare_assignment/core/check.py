import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from git import Git

from prepare_assignment.core.versions import COMMIT_HASH_RE, get_git_url, get_web_url, highest_tag, \
    list_remote_tags, remote_ref, resolve_version_from_tags
from prepare_assignment.data.task_properties import TaskProperties
from prepare_assignment.utils.tasks import get_all_tasks, load_task

logger = logging.getLogger("prepare_assignment")


@dataclass
class TaskStatus:
    task: TaskProperties
    # The installed version (tag or short commit hash), None if not installed
    installed: Optional[str] = None
    # Newer version that matches the requested version (e.g. v1 → v1.2.0), None if up-to-date
    update: Optional[str] = None
    # Newest version overall, only set if it is newer than what the requested version resolves to
    newest: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None

    def __str__(self) -> str:
        prefix = f"{self.task}: "
        if self.error is not None:
            return prefix + f"unable to check ({self.error})"
        if self.installed is None:
            return prefix + f"not installed (use 'prepare task add {self.task}')"
        text = self.installed
        if self.update is not None:
            text += f" → {self.update}"
        else:
            text += ", up to date"
        if self.newest is not None:
            text += f" (newest: {self.newest})"
        if self.url is not None:
            text += f" {self.url}"
        return prefix + text


def __short(sha: str) -> str:
    return sha[:7]


def __local_head(props: TaskProperties) -> str:
    # Use the git cli, GitPython cannot read repositories that use the reftable format
    return str(Git(str(props.repo_path)).rev_parse("HEAD")).strip()


def check_task(props: TaskProperties) -> TaskStatus:
    """
    Check whether there is a newer version available for an (installed) task
    """
    status = TaskStatus(props)
    if not props.definition_path.is_file():
        return status
    try:
        git_url = get_git_url(props)
        web_url = get_web_url(props)
        head = __local_head(props)
        tags = list_remote_tags(git_url)
        newest = highest_tag(list(tags.keys()))

        # The installed tag (if any)
        installed_tags = [tag for tag, sha in tags.items() if sha == head]
        installed_tag = highest_tag(installed_tags) or (installed_tags[0] if installed_tags else None)
        status.installed = installed_tag or __short(head)

        if COMMIT_HASH_RE.match(props.version):
            # Pinned to a commit, only report newer releases
            target = None
        elif props.version == "main" or (props.version == "latest" and newest is None):
            remote = remote_ref(git_url, "main" if props.version == "main" else "HEAD")
            if remote is not None and remote != head:
                status.update = __short(remote)
                status.url = f"{web_url}/compare/{head}...{remote}"
            if newest is not None and newest != installed_tag:
                status.newest = newest
            return status
        else:
            target = resolve_version_from_tags(list(tags.keys()), props.version)

        if target is not None and target in tags and tags[target] != head:
            status.update = target
            status.url = f"{web_url}/releases/tag/{target}"
        if newest is not None and newest != (status.update or installed_tag):
            status.newest = newest
            if status.url is None:
                status.url = f"{web_url}/releases/tag/{newest}"
    except Exception as e:
        status.error = str(e).splitlines()[0] if str(e) else type(e).__name__
    return status


def __collect(props: TaskProperties, collected: Dict[str, TaskProperties]) -> None:
    if str(props) in collected:
        return
    collected[str(props)] = props
    if not props.definition_path.is_file():
        return
    try:
        task = load_task(props)
    except Exception as e:
        logger.debug(f"Unable to load task '{props}': {e}")
        return
    if task.is_composite:
        for step in task.tasks:  # type: ignore
            uses = step.get("uses", None)
            if uses is not None:
                __collect(TaskProperties.of(uses), collected)


def tasks_in_prepare(yaml: Dict[str, Any]) -> List[TaskProperties]:
    """
    All tasks used by a prepare file, including the (installed) sub-tasks of composite tasks
    """
    collected: Dict[str, TaskProperties] = {}
    for steps in (yaml.get("jobs", None) or {}).values():
        for step in steps or []:
            uses = step.get("uses", None)
            if uses is not None:
                __collect(TaskProperties.of(uses), collected)
    return list(collected.values())


def check(tasks: List[TaskProperties]) -> List[TaskStatus]:
    seen: Set[str] = set()
    result: List[TaskStatus] = []
    for props in tasks:
        if str(props) in seen:
            continue
        seen.add(str(props))
        result.append(check_task(props))
    return result


def check_all() -> List[TaskStatus]:
    return check(sorted(get_all_tasks(), key=str))
