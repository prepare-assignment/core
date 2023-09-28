import argparse
import logging
import os
from pathlib import Path
from typing import Optional

from prepare_toolbox.file import get_matching_files
from ruamel.yaml import YAML

from prepare_assignment.core.preparer import prepare_actions
from prepare_assignment.core.runner import run
from prepare_assignment.core.validator import validate_prepare
from prepare_assignment.data.errors import ValidationError, DependencyError
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
                        help="increase action output verbosity",
                        default=0)
    parser.add_argument("-d",
                        "--debug",
                        action="count",
                        help="increase debug verbosity for prepare assignment",
                        default=0)


def __get_prepare_file(file: Optional[str]) -> str:
    """
    Try and find the correct prepare_assignment.y(a)ml
    :param file: file name provided by the user
    :return: path to file
    :raises FileNotFoundError: if file doesn't exist
    :raises AssertionError: if there is both a prepare_assignment.yml and a prepare_assignment.yml and no file is provided by the user
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
    Parse 'prepare_assignment.y(a)ml' and execute all steps
    """
    # Handle command line arguments
    parser = argparse.ArgumentParser()
    add_commandline_arguments(parser)
    args = parser.parse_args()

    # Set the logger
    add_logging_level("TRACE", logging.DEBUG - 5, "trace")
    logger = logging.getLogger("prepare_assignment")
    actions_logger = logging.getLogger("actions")
    set_logger_level(logger, args.debug)
    set_logger_level(actions_logger, args.verbosity, new_lines=False)

    # Get the prepare_assignment.yml file
    file = __get_prepare_file(args.file)
    logger.info(f"Found prepare_assignment config file at: {file}")

    # Load the file
    yaml = YAML(typ='safe')
    path = Path(file)
    prepare = yaml.load(path)

    # Execute all steps
    os.chdir(os.path.dirname(path))
    try:
        validate_prepare(file, prepare)
        mapping = prepare_actions(file, prepare['steps'])
        run(prepare, mapping)
    except ValidationError as ve:
        logger.error(ve.message)
    except DependencyError as de:
        logger.error(de.message)
