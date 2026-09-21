import logging
import os.path
from pathlib import Path
from typing import Set

import typer
from treelib import Tree

from prepare_assignment.core.preparer import __prepare_tasks
from prepare_assignment.core.versions import get_git_url, is_fixed_version
from prepare_assignment.data.task_definition import TaskDefinition
from prepare_assignment.data.task_properties import TaskProperties
from prepare_assignment.utils.files import remove_tree
from prepare_assignment.utils.dependency import get_dependencies
from prepare_assignment.utils.paths import get_tasks_path
from prepare_assignment.utils.tasks import get_all_tasks
from prepare_assignment.utils.yml_loader import YAML_LOADER

logger = logging.getLogger("prepare_assignment")
tasks_path = get_tasks_path()


def remove(task: str, recursive: bool) -> None:
    props = TaskProperties.of(task)
    dependencies = get_dependencies(props)

    all_tasks = set(get_all_tasks())
    not_used_tasks = all_tasks - dependencies
    other_dependencies = get_dependencies(not_used_tasks)

    if not (dependencies - other_dependencies) == dependencies:
        raise AssertionError(f"Cannot remove {task}, "
                             f"as there are other tasks dependent on this task or on a dependency of this task")

    if not recursive:
        remove_tree(props.task_path)
    else:
        for dep in dependencies:
            remove_tree(dep.task_path)


def update(task: str, recursive: bool) -> None:
    props = TaskProperties.of(task)
    dependencies: Set[TaskProperties] = get_dependencies(props) if recursive else {props}
    # TODO: use topological sort to make sure the order we remove and reinstall is the most efficient
    for dep in dependencies:
        # Only update versions that can move (latest, main, v1, branches), not exact tags or commits
        # Tags in git are not immutable, but we ignore that for now
        if not is_fixed_version(get_git_url(dep), dep.version):
            __reinstall(dep)


def __reinstall(props: TaskProperties) -> None:
    """
    Reinstall a task, if the installation fails the previous installation is restored
    """
    if not os.path.isdir(props.task_path):
        add(str(props))
        return
    backup = Path(f"{props.task_path}.backup")
    remove_tree(backup)
    os.replace(props.task_path, backup)
    try:
        add(str(props))
    except Exception:
        remove_tree(props.task_path, ignore_errors=True)
        os.replace(backup, props.task_path)
        raise
    remove_tree(backup, ignore_errors=True)


def remove_all() -> None:
    remove_tree(tasks_path)


def ls() -> None:
    if not os.path.isdir(tasks_path):
        print("No tasks available")
        return
    tree = Tree()
    organizations = sorted(os.listdir(tasks_path))
    for org in organizations:
        tree.create_node(org, org)
        org_path = os.path.join(tasks_path, org)
        tasks = sorted(os.listdir(org_path))
        for task in tasks:
            tree.create_node(task, task, parent=org)
            version_path = os.path.join(org_path, task)
            versions = sorted(os.listdir(version_path))
            for version in versions:
                tree.create_node(version, parent=task)
    t = tree.show(stdout=False)
    print(t)


def info(task: str) -> None:
    props = TaskProperties.of(task)
    if not os.path.isfile(props.definition_path):
        logger.error(f"Path '{props.definition_path}' doesn't exist")
        raise typer.Abort()
    yaml = YAML_LOADER.load(props.definition_path)
    task_def = TaskDefinition.of(yaml, props.task_path)
    print(task_def)


def add(task: str) -> None:
    tasks = [{"uses": task}]
    __prepare_tasks(tasks, check_inputs=False)


