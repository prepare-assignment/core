import os
from typing import List

from prepare_assignment.data.constants import YAML_LOADER
from prepare_assignment.data.task_definition import TaskDefinition
from prepare_assignment.data.task_properties import TaskProperties
from prepare_assignment.utils.cache import get_tasks_path


def get_all_tasks() -> List[TaskProperties]:
    tasks_path = get_tasks_path()
    tasks: List[TaskProperties] = []
    if not os.path.isdir(tasks_path):
        return tasks

    for org in os.listdir(tasks_path):
        org_path = os.path.join(tasks_path, org)
        task_dirs = os.listdir(org_path)
        for task in task_dirs:
            version_path = os.path.join(org_path, task)
            versions = os.listdir(version_path)
            for version in versions:
                tasks.append(TaskProperties.of(f"{org}/{task}@{version}"))
    return tasks


def load_task(props: TaskProperties) -> TaskDefinition:
    yaml = YAML_LOADER.load(props.definition_path)
    task = TaskDefinition.of(yaml, props.definition_path)
    return task
