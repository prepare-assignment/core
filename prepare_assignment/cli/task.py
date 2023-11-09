import typer

from prepare_assignment.core.tasks import info, remove, update, add

app = typer.Typer(help="Commands that apply to one task")


@app.command("info")
def display_info(task: str) -> None:
    """
    Display task info
    """
    info(task)


@app.command("remove")
def display_remove(task: str) -> None:
    """
    Remove a task
    """
    remove(task)


@app.command("update")
def display_update(task: str) -> None:
    """
    Update a task
    """
    update(task)


@app.command("add")
def display_add(task: str) -> None:
    """
    Add a task
    """
    add(task)
