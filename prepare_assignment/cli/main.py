import os.path
import sys
from typing import Dict, List, Optional

import typer
from typing_extensions import Annotated

from prepare_assignment import __version__
from prepare_assignment.cli.task import app as task_app
from prepare_assignment.cli.tasks import app as tasks_app
from prepare_assignment.core.main import prepare
from prepare_assignment.data.config import GitMode
from prepare_assignment.data.constants import CONFIG
from prepare_assignment.utils.paths import get_config_path
from prepare_assignment.utils.virtual_env import get_virtualenv_name

app = typer.Typer(invoke_without_command=True)
app.add_typer(task_app, name="task")
app.add_typer(tasks_app, name="tasks")


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        config_path = os.path.join(get_config_path(), 'config.yml')
        config_exists = os.path.exists(config_path)
        typer.echo(f"Prepare version: {__version__}")
        typer.echo(f"Config in use: {config_exists}")
        typer.echo(f"Config path: {config_path}")
        typer.echo(f"Python version: {sys.version.split(' ')[0]}")
        typer.echo(f"Virtual env: {get_virtualenv_name()}")


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def run(
    ctx: typer.Context,
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
    ] = CONFIG.core.verbose,
    env: Annotated[
        Optional[List[str]],
        typer.Option("-e", "--env", help="Set environment variable (KEY=VALUE)")
    ] = None,
):
    """
    Parse 'prepare_assignment.y(a)ml' and execute all jobs
    """
    CONFIG.core.debug = debug  # type: ignore
    CONFIG.core.git_mode = git # type: ignore
    CONFIG.core.verbose = verbose  # type: ignore

    env_vars: Dict[str, str] = {}
    for item in (env or []):
        key, _, value = item.partition("=")
        env_vars[key] = value
    # ctx.args only contains arguments unknown to Click (known options like --debug,
    # --verbose are consumed by the parser and never appear here)
    for arg in ctx.args:
        if arg.startswith("--"):
            env_vars[arg[2:]] = "true"

    try:
        prepare(file_name, env_vars)
    except Exception:
        raise typer.Exit(code=1)
