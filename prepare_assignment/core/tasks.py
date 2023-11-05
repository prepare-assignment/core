import logging
import os.path
import sys
from pathlib import Path

import typer
from treelib import Tree

from prepare_assignment.data.prepare import Prepare
from prepare_assignment.data.task_definition import TaskDefinition
from prepare_assignment.data.task_properties import TaskProperties
from prepare_assignment.utils.cache import get_tasks_path
from prepare_assignment.data.constants import YAML_LOADER

logger = logging.getLogger("prepare_assignment")


def remove(task: str) -> None:
    print("Removing")


def update(task: str) -> None:
    print("Updating")


def remove_all() -> None:
    confirm_remove = typer.confirm("Are you sure you want to remove all tasks?")
    if not confirm_remove:
        print("Not deleting")
        raise typer.Abort()
    print("Removing all")


def ls() -> None:
    tasks_path = get_tasks_path()
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
    yml_path = os.path.join(get_tasks_path(), props.organization, props.name, props.version, "repo", "task.yml")
    if not os.path.isfile(yml_path):
        print(f"Path '{yml_path}' doesn't exist", file=sys.stderr)
        typer.Abort()
    path = Path(yml_path)
    yaml = YAML_LOADER.load(path)
    task = TaskDefinition.of(yaml, yml_path)
    print(task)
