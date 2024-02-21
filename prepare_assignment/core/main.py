import logging
import os
from pathlib import Path
from typing import Optional

from prepare_toolbox.file import get_matching_files

from prepare_assignment.core.preparer import prepare_tasks
from prepare_assignment.core.runner import run
from prepare_assignment.core.validator import validate_prepare
from prepare_assignment.data.constants import CONFIG, YAML_LOADER
from prepare_assignment.data.errors import PrepareTaskError, PrepareError
from prepare_assignment.data.prepare import Prepare
from prepare_assignment.utils.logger import add_logging_level, set_logger_level


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
        files = get_matching_files("prepare.y{,a}ml")
        if len(files) == 0:
            raise FileNotFoundError("No prepare.yml file found in working directory")
        elif len(files) > 1:
            raise AssertionError("There is both a prepare.yml and a prepare.yml,"
                                 " use the -f flag to specify which file to use")
        file = files[0]
    else:
        file = str(Path(os.path.join(os.getcwd(), file)))
        if not os.path.isfile(file):
            raise FileNotFoundError(f"Supplied file: '{file}' is not a file")
    return file


def prepare(file_name: Optional[str]) -> None:
    # Set the logger
    add_logging_level("TRACE", logging.DEBUG - 5, "trace")
    logger = logging.getLogger("prepare_assignment")
    tasks_logger = logging.getLogger("tasks")
    set_logger_level(logger, CONFIG.DEBUG)
    set_logger_level(tasks_logger, CONFIG.VERBOSITY, prefix="\t[TASK] ", debug_linenumbers=False)

    try:
        # Get the prepare_assignment.yml file
        file = __get_prepare_file(file_name)
        logger.debug(f"Found prepare_assignment config file at: {file}")

        # Load the file
        path = Path(file)
        yaml = YAML_LOADER.load(path)

        # Check if we have to change working directory
        dirname = os.path.dirname(path)
        if dirname:
            os.chdir(dirname)

        # Prepare
        validate_prepare(file, yaml)
        mapping = prepare_tasks(file, yaml['jobs'])
        prepare = Prepare.of(yaml)

        # Execute
        run(prepare, mapping)
    except PrepareTaskError as PE:
        logger.error(PE.message)
        if isinstance(PE.cause, PrepareError):
            logger.error(PE.cause.message)
        else:
            logger.error(str(PE.cause))
    except Exception as e:
        logger.error(str(e))