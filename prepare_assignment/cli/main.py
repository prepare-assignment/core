from typing import Optional

import typer
from typing_extensions import Annotated

from prepare_assignment.cli.task import app as task_app
from prepare_assignment.cli.tasks import app as tasks_app
from prepare_assignment.core.main import prepare
from prepare_assignment.data.config import GitMode
from prepare_assignment.data.constants import CONFIG
from prepare_assignment.utils.config import load_config

load_config()
app = typer.Typer(invoke_without_command=False)
app.add_typer(task_app, name="task")
app.add_typer(tasks_app, name="tasks")


@app.command()
def run(
    file_name: Annotated[
        Optional[str],
        typer.Option("--file", "-f", help="Configuration file")
    ] = None,
    git: Annotated[
        GitMode,
        typer.Option(case_sensitive=False, help="Clone mode for git, options are 'ssh' (default) or 'https'")
    ] = CONFIG.core.git_mode,
    debug: Annotated[
        int,
        typer.Option("--debug", "-d", count=True, help="increase debug verbosity for prepare assignment")
    ] = CONFIG.core.debug,
    verbose: Annotated[
        int,
        typer.Option("--verbose", "-v", count=True, help="increase task output verbosity")
    ] = CONFIG.core.verbose
):
    """
    Parse 'prepare_assignment.y(a)ml' and execute all jobs
    """
    CONFIG.core.debug = debug  # type: ignore
    CONFIG.core.git_mode = git # type: ignore
    CONFIG.core.verbose = verbose  # type: ignore

    prepare(file_name)

