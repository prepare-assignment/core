from typing import Set

from multipledispatch import dispatch  # type: ignore

from prepare_assignment.data.task_properties import TaskProperties
from prepare_assignment.utils.tasks import load_task


def __get_dependencies(tasks: Set[TaskProperties], visited: Set[TaskProperties]) -> None:
    if len(tasks) == 0:
        return
    task_properties = tasks.pop()
    task = load_task(task_properties)
    if task.is_composite:
        for dep in task.tasks:  # type: ignore
            if not dep.get("uses", None):
                continue
            prop = TaskProperties.of(dep["uses"])
            if prop not in visited:
                tasks.add(prop)
    visited.add(task_properties)
    __get_dependencies(tasks, visited)


@dispatch(TaskProperties)
def get_dependencies(task: TaskProperties) -> Set[TaskProperties]:
    return get_dependencies({task})


@dispatch(set)  # type: ignore
def get_dependencies(tasks: Set[TaskProperties]) -> Set[TaskProperties]:
    visited = set()
    __get_dependencies(set(tasks), visited)
    return visited
