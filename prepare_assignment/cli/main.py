import os.path
import sys
from pathlib import Path
from typing import Dict, List, Optional

import typer
from typing_extensions import Annotated

from prepare_assignment import __version__
from prepare_assignment.cli.task import app as task_app
from prepare_assignment.cli.tasks import app as tasks_app
from prepare_assignment.core.check import check as check_tasks, check_all, tasks_in_prepare
from prepare_assignment.core.main import prepare, get_prepare_file
from prepare_assignment.data.config import GitMode
from prepare_assignment.data.constants import CONFIG
from prepare_assignment.utils.paths import get_config_path
from prepare_assignment.utils.virtual_env import get_virtualenv_name
from prepare_assignment.utils.yml_loader import YAML_LOADER

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
        if "=" not in item:
            raise typer.BadParameter("Environment variables must be in KEY=VALUE format.", param_hint="-e/--env")
        key, value = item.split("=", 1)
        if not key:
            raise typer.BadParameter("Environment variable name cannot be empty.", param_hint="-e/--env")
        env_vars[key] = value
    # ctx.args only contains arguments unknown to Click (known options like --debug,
    # --verbose are consumed by the parser and never appear here)
    for arg in ctx.args:
        if not arg.startswith("--"):
            continue
        key_value = arg[2:]
        if not key_value:
            continue
        if "=" in key_value:
            key, value = key_value.split("=", 1)
            if not key:
                continue
        else:
            key, value = key_value, "true"
        env_vars[key] = value

    try:
        prepare(file_name, env_vars)
    except Exception:
        raise typer.Exit(code=1)


@app.command()
def check(
    file_name: Annotated[
        Optional[str],
        typer.Option("--file", "-f", help="Configuration file")
    ] = None,
    all_tasks: Annotated[
        bool,
        typer.Option("--all", "-a", help="Check all installed tasks instead of the tasks used in the prepare file")
    ] = False,
    git: Annotated[
        GitMode,
        typer.Option(case_sensitive=False, help="Mode for git, options are 'ssh' (default) or 'https'")
    ] = CONFIG.core.git_mode,
):
    """
    Check which tasks have newer versions available
    """
    CONFIG.core.git_mode = git  # type: ignore
    if all_tasks:
        statuses = check_all()
    else:
        try:
            file = get_prepare_file(file_name)
        except (FileNotFoundError, AssertionError) as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(code=1)
        statuses = check_tasks(tasks_in_prepare(YAML_LOADER.load(Path(file))))
    if len(statuses) == 0:
        typer.echo("No tasks to check")
    for status in statuses:
        typer.echo(str(status))
