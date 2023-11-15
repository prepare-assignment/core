import typer

from prepare_assignment.core.task_handler import ls, remove_all

app = typer.Typer(help="Apply action to all tasks")


@app.command("ls")
def display_ls() -> None:
    """
    List all tasks
    """
    ls()


@app.command("remove")
def display_remove() -> None:
    """
    Remove all tasks
    """
    confirm_remove = typer.confirm("Are you sure you want to remove all tasks?")
    if not confirm_remove:
        raise typer.Abort()
    remove_all()
