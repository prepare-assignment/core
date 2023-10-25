import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, TypedDict

from git import Repo
from importlib_resources import files
from virtualenv import cli_run  # type: ignore

from prepare_assignment.core.validator import validate_action_definition, validate_action, load_yaml, \
    validate_default_values
from prepare_assignment.data.action_definition import ActionDefinition, CompositeActionDefinition, \
    PythonActionDefinition
from prepare_assignment.data.action_properties import ActionProperties
from prepare_assignment.data.constants import CONFIG
from prepare_assignment.data.errors import DependencyError, ValidationError
from prepare_assignment.utils.cache import get_cache_path

# Set the cache path
cache_path = get_cache_path()
# Get the logger
logger = logging.getLogger("prepare_assignment")
# Load the actions template file
template_file = files().joinpath('../schemas/actions.schema.json_template')
template: str = template_file.read_text()


def __repo_path(props: ActionProperties) -> Path:
    return Path(os.path.join(cache_path, props.organization, props.name, props.version, "repo"))


def __download_action(props: ActionProperties) -> Path:
    """
    Download (using git clone) the action
    :param props: action properties
    :returns Path: the path where the repo is checked out
    """
    path: Path = __repo_path(props)
    path.mkdir(parents=True, exist_ok=True)
    if CONFIG.GIT_MODE == "https":
        git_url: str = f"git@github.com:{props.organization}/{props.name}.git"
    else:
        git_url: str = f"https://github.com/{props.organization}/{props.name}.git"
    logger.debug(f"Cloning repository: {git_url}")
    with Repo.clone_from(git_url, path) as repo:
        if props.version != "latest":
            logger.debug(f"Checking out correct version of repository: {props.version}")
            repo.git.checkout(props.version)
    return path


def __build_json_schema(props: ActionProperties, action: ActionDefinition) -> str:
    logger.debug(f"Building json schema for '{action.id}'")
    schema = template.replace("{{action-id}}", action.id)
    schema = schema.replace("{{action-version}}", props.version)
    schema = schema.replace("{{organization}}", props.organization)
    schema = schema.replace("{{action}}", str(props))
    schema = schema.replace("{{action-name}}", action.name)
    schema = schema.replace("{{action-description}}", action.description)
    required: List[str] = []
    properties: List[str] = []
    for inp in action.inputs:
        properties.append(inp.to_schema_definition())
        if inp.required:
            required.append(inp.name)
    if len(properties) > 0:
        output = ',    \n"with": {\n      "type": "object",\n      "additionalProperties": false,\n      "properties": {\n'
        output += ",\n".join(properties) + "\n    }"
        if len(required) > 0:
            schema = schema.replace("{{required}}", ', "with"')
            output += ',\n    "required": [' + ", ".join(map(lambda x: f'"{x}"', required)) + ']\n    }'
        else:
            schema = schema.replace("{{required}}", "")
            output += "\n}"
        schema = schema.replace("{{with}}", output)
    return schema


def __action_properties(action: str) -> ActionProperties:
    parts = action.split("/")
    if len(parts) > 2:
        raise AssertionError("Actions cannot have more than one slash")
    elif len(parts) == 1:
        parts.insert(0, "prepare-assignment")
    organization: str = parts[0]
    name = parts[1]
    split = name.split("@")
    version: str = "latest"
    action_name: str = name
    if len(split) > 2:
        raise AssertionError("Cannot have multiple '@' symbols in the name")
    elif len(split) == 2:
        action_name = split[0]
        version = split[1]
    return ActionProperties(organization, action_name, version)


def __action_dict_to_definition(action: Any, path: str) -> ActionDefinition:
    if action["runs"]["using"] == "composite":
        return CompositeActionDefinition.of(action, path)
    else:
        return PythonActionDefinition.of(action, path)


def __action_install_dependencies(action_path: str) -> None:
    if sys.platform == "win32":
        venv_path = os.path.join(action_path, "venv", "scripts", "python.exe")
    else:
        venv_path = os.path.join(action_path, "venv", "bin", "python")
    repo_path = os.path.join(action_path, "repo")
    requirements_path = os.path.join(repo_path, "requirements.txt")
    pyproject_path = os.path.join(repo_path, "pyproject.toml")
    has_requirements = os.path.isfile(requirements_path)
    has_pyproject = os.path.isfile(pyproject_path)

    if not has_requirements and not has_pyproject:
        return

    result: Optional[subprocess.CompletedProcess[Any]] = None
    if has_requirements:
        logger.debug(f"Installing dependencies from '{requirements_path}'")
        args = [venv_path] + f"-m pip install -r {requirements_path}".split(" ")
        result = subprocess.run(args, capture_output=True)
    elif has_pyproject:
        logger.debug(f"Installing dependencies from '{pyproject_path}'")
        args = [venv_path] + f"-m pip install .".split()
        result = subprocess.run(args, capture_output=True, cwd=repo_path)

    if result is not None and result.returncode == 1:
        log_path = os.path.join(cache_path, "logs")
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file = os.path.join(log_path, f'{timestamp}-dependencies.log')
        Path(log_path).mkdir(parents=True, exist_ok=True)
        with open(file, 'wb') as handle:
            handle.write(result.stderr)
        raise DependencyError(f"Unable to install dependencies for '{repo_path}', see '{file}' for more info")


class ActionStuff(TypedDict):
    schema: Any
    action: ActionDefinition


def __load_action_from_disk(action_name: str,
                            action_path: str,
                            props: ActionProperties,
                            parsed: Dict[str, ActionStuff]
                            ) -> None:
    logger.debug(f"Action '{action_name}' is already available, loading from disk")
    repo_path = __repo_path(props)
    yaml_path = os.path.join(repo_path, "action.yml")
    with open(os.path.join(action_path, f"{props.name}.schema.json"), "r") as handle:
        json_schema = json.load(handle)
    action_yaml = load_yaml(yaml_path)
    action = __action_dict_to_definition(action_yaml, action_path)
    parsed[action_name] = {"schema": json_schema, "action": action}
    if isinstance(action, CompositeActionDefinition):
        for subaction in action.steps:
            subaction_name = subaction.get("uses", None)
            if subaction_name is None:
                continue
            subprops = __action_properties(subaction_name)
            action_path = os.path.join(cache_path, subprops.organization, subprops.name, subprops.version)
            __load_action_from_disk(subaction_name, action_path, subprops, parsed)


def __prepare_actions(file: str, actions: List[Any], parsed: Optional[Dict[str, ActionStuff]] = None) \
        -> Dict[str, ActionStuff]:
    # Unfortunately we cannot do this as a default value, see:
    # https://docs.python-guide.org/writing/gotchas/#mutable-default-arguments
    if parsed is None:
        parsed = {}
    if len(actions) == 0:
        logger.debug("All (sub-)actions prepared")
        return parsed

    action_def = actions.pop()
    act: str = action_def["uses"]
    json_schema: Optional[Any] = None
    # Check if we have already loaded the action
    if parsed.get(act, None) is None:
        logger.debug(f"Action '{act}' has not been loaded in this run")
        props = __action_properties(act)

        # Check if action (therefore the path) has already been downloaded in previous run
        action_path = os.path.join(cache_path, props.organization, props.name, props.version)
        action: Optional[ActionDefinition] = None
        repo_path = __repo_path(props)
        yaml_path = os.path.join(repo_path, "action.yml")
        if os.path.isdir(action_path):
            __load_action_from_disk(act, action_path, props, parsed)
        else:
            logger.debug(f"Action '{act}' is not available on this system")
            # Download the action (clone the repository)
            __download_action(props)
            # Validate that the action.yml is valid
            action_yaml = validate_action_definition(yaml_path)
            action = __action_dict_to_definition(action_yaml, action_path)
            validate_default_values(action)
            # Check if it is a composite action, in that case we might need to retrieve more actions
            if isinstance(action, CompositeActionDefinition):
                logger.debug(f"Action '{act}' is a composite action, preparing sub-actions")
                all_actions: List[Any] = []
                for step in action.steps:
                    name = step.get("uses", None)
                    if name is not None:
                        all_actions.append(step)
                parsed = __prepare_actions(str(repo_path), all_actions, parsed)
            else:
                main_path = os.path.join(repo_path, action.main)  # type: ignore
                if not os.path.isfile(main_path):
                    raise ValidationError(f"Main file '{action.main}' does not exist for action '{action.name}'") # type: ignore
            # Now we can build a schema for this action
            schema = __build_json_schema(props, action)
            json_schema = json.loads(schema)
            with open(os.path.join(action_path, f"{props.name}.schema.json"), 'w') as handle:
                handle.write(schema)
            # Create a virtualenv for this action
            cli_run([os.path.join(action_path, "venv")])
            # Install dependencies
            __action_install_dependencies(action_path)
            parsed[act] = {"schema": json_schema, "action": action}
            if action_def.get("with", None) is None:
                action_def["with"] = {}
    validate_action(file, action_def, parsed[act]["schema"])
    return __prepare_actions(file, actions, parsed)


def prepare_actions(prepare_file: str, steps: Dict[str, Any]) -> Dict[str, ActionDefinition]:
    """
    Make sure that the actions are available for the runner.

    If an action is not available:
    1. Clone the repository
    2. Checkout the correct version
    3. Generate json schema for validation
    4. Validate action

    :param prepare_file the name/path to the prepare file
    :param steps: The actions of the prepare file
    :return: None
    """
    logger.debug("========== Preparing actions")
    all_actions: List[Any] = []
    # DON'T FORGET TO REMOVE, ONLY FOR DEVELOPMENT
    # shutil.rmtree(cache_path, ignore_errors=True)
    # Iterate through all the actions to make sure that they are available
    for step, actions in steps.items():
        for action in actions:
            # If the action is a run command, we don't need to do anything
            if action.get("uses", None) is not None:
                all_actions.append(action)
    mapping = __prepare_actions(prepare_file, all_actions)
    logger.debug("✓ All actions downloaded and valid")
    return {k: v["action"] for k, v in mapping.items()}
