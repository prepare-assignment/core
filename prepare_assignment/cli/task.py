import logging
from typing import Optional

import typer
from typing_extensions import Annotated

from prepare_assignment.core.task_handler import info, remove, update, add

app = typer.Typer(help="Commands that apply to one task")
logger = logging.getLogger("prepare_assignment")


@app.command("info")
def display_info(task: str) -> None:
    """
    Display task info
    """
    info(task)


@app.command("remove")
def display_remove(
        task: Annotated[str, typer.Argument(help="The task to remove")],
        recursive: Annotated[
            bool,
            typer.Option("-r", "--recursive", help="Recursively remove dependencies as well")
        ] = False
) -> None:
    """
    Remove a task
    """
    try:
        remove(task, recursive)
    except Exception as e:
        logger.exception(e)
        raise typer.Abort()


@app.command("update")
def display_update(
        task: Annotated[str, typer.Argument(help="The task to remove")],
        recursive: Annotated[
            bool,
            typer.Option("-r", "--recursive", help="Recursively remove dependencies as well")
        ] = False) -> None:
    """
    Update a task
    """
    try:
        update(task, recursive)
    except Exception as e:
        logger.exception(e)
        typer.Abort()


@app.command("add")
def display_add(task: str) -> None:
    """
    Add a task
    """
    add(task)
