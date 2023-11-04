import argparse
import logging
import os
from pathlib import Path
from typing import Optional

from prepare_toolbox.file import get_matching_files
from ruamel.yaml import YAML

from prepare_assignment.core.preparer import prepare_tasks
from prepare_assignment.core.runner import run
from prepare_assignment.core.validator import validate_prepare
from prepare_assignment.data.constants import CONFIG
from prepare_assignment.data.errors import ValidationError, DependencyError, PrepareTaskError, PrepareError
from prepare_assignment.data.prepare import Prepare
from prepare_assignment.utils import set_logger_level
from prepare_assignment.utils.logger import add_logging_level


def add_commandline_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Add command line arguments to the argparser
    :param parser: The parser to add the arguments to
    """
    parser.add_argument("-f", "--file", action="store", help="Configuration file")
    parser.add_argument("-v",
                        "--verbosity",
                        action="count",
                        help="increase task output verbosity",
                        default=0)
    parser.add_argument("-d",
                        "--debug",
                        action="count",
                        help="increase debug verbosity for prepare assignment",
                        default=0)
    parser.add_argument("-g",
                        "--git",
                        nargs="?",
                        const="ssh",
                        default="ssh",
                        choices=["ssh", "https"],
                        help="Clone mode for git, options are 'ssh' (default) or 'https'")


def __get_prepare_file(file: Optional[str]) -> str:
    """
    Try and find the correct prepare_assignment.y(a)ml
    :param file: file name provided by the user
    :return: path to file
    :raises FileNotFoundError: if file doesn't exist
    :raises AssertionError: if there is both a prepare_assignment.yml and a prepare_assignment.yml
                            and no file is provided by the user
    :raises FileNotFoundError: if the provided 'file' is not a file
    """
    if file is None:
        files = get_matching_files("prepare_assignment.y{,a}ml")
        if len(files) == 0:
            raise FileNotFoundError("No prepare_assignment.yml file found in working directory")
        elif len(files) > 1:
            raise AssertionError("There is both a prepare_assignment.yml and a prepare_assignment.yml,"
                                 " use the -f flag to specify which file to use")
        file = files[0]
    else:
        file = str(Path(os.path.join(os.getcwd(), file)))
        if not os.path.isfile(file):
            raise FileNotFoundError(f"Supplied file: '{file}' is not a file")
    return file


def main() -> None:
    """
    Parse 'prepare_assignment.y(a)ml' and execute all jobs
    """
    # Handle command line arguments
    parser = argparse.ArgumentParser()
    add_commandline_arguments(parser)
    args = parser.parse_args()
    CONFIG.DEBUG = args.debug  # type: ignore
    CONFIG.GIT_MODE = args.git  # type: ignore
    CONFIG.VERBOSITY = args.verbosity  # type: ignore

    # Set the logger
    add_logging_level("TRACE", logging.DEBUG - 5, "trace")
    logger = logging.getLogger("prepare_assignment")
    tasks_logger = logging.getLogger("tasks")
    set_logger_level(logger, args.debug)
    set_logger_level(tasks_logger, args.verbosity, prefix="\t[TASK] ", debug_linenumbers=False)

    # Get the prepare_assignment.yml file
    file = __get_prepare_file(args.file)
    logger.debug(f"Found prepare_assignment config file at: {file}")

    # Load the file
    loader = YAML(typ='safe')
    path = Path(file)
    yaml = loader.load(path)

    # Execute all jobs
    os.chdir(os.path.dirname(path))
    try:
        validate_prepare(file, yaml)
        mapping = prepare_tasks(file, yaml['jobs'])
        prepare = Prepare.of(yaml)
        run(prepare, mapping)
    except PrepareTaskError as PE:
        logger.error(PE.message)
        if isinstance(PE.cause, PrepareError):
            logger.error(PE.cause.message)
        else:
            logger.error(str(PE.cause))
    except Exception as e:
        logger.error(str(e))
