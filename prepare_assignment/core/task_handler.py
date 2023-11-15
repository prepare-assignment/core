import logging
import os.path
import shutil
import sys
from pathlib import Path
from typing import Set

import typer
from treelib import Tree

from prepare_assignment.core.preparer import __prepare_tasks
from prepare_assignment.data.constants import YAML_LOADER
from prepare_assignment.data.task_definition import TaskDefinition
from prepare_assignment.data.task_properties import TaskProperties
from prepare_assignment.utils.cache import get_tasks_path
from prepare_assignment.utils.dependency import get_dependencies
from prepare_assignment.utils.tasks import get_all_tasks

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
        shutil.rmtree(props.task_path)
    else:
        for dep in dependencies:
            shutil.rmtree(dep.task_path)


def update(task: str, recursive: bool) -> None:
    props = TaskProperties.of(task)
    dependencies: Set[TaskProperties] = get_dependencies(props) if recursive else {props}
    # TODO: use topological sort to make sure the order we remove and reinstall is the most efficient
    for dep in dependencies:
        # Only update if version is 'latest'
        # Tags in git are not immutable, but we ignore that for now
        if dep.version == "latest":
            # Easiest way is to just remove and reinstall
            shutil.rmtree(dep.task_path)
            add(str(dep))


def remove_all() -> None:
    shutil.rmtree(tasks_path)


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
        print(f"Path '{props.definition_path}' doesn't exist", file=sys.stderr)
        typer.Abort()
    yaml = YAML_LOADER.load(props.definition_path)
    task_def = TaskDefinition.of(yaml, props.definition_path)
    print(task_def)


def add(task: str) -> None:
    tasks = [{"uses": task}]
    __prepare_tasks(tasks, check_inputs=False)


