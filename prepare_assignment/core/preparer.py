import json
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional

from git import Repo
from importlib_resources import files

from prepare_assignment.core.validator import validate_action_definition, validate_action
from prepare_assignment.data.action_definition import ActionDefinition, CompositeActionDefinition
from prepare_assignment.data.action_properties import ActionProperties
from prepare_assignment.utils.cache import get_cache_path

# Set the cache path
cache_path = get_cache_path()
# Get the logger
logger = logging.getLogger("prepare")
# Load the actions template file
template_file = files().joinpath('../schemas/actions.schema.json_template')
template: str = template_file.read_text()


def __download_action(organization: str, action: str, version: str) -> Path:
    """
    Download (using git clone) the action
    :param organization: GitHub organization/username
    :param action: action name
    :returns str: the path where the repo is checked out
    """
    path: Path = Path(os.path.join(cache_path, organization, action, version, "repo"))
    path.mkdir(parents=True, exist_ok=True)
    # For now use ssh protocol, need to figure out how to use system defined one
    git_url: str = f"git@github.com:{organization}/{action}.git"
    logger.debug(f"Cloning repository: {git_url}")
    repo = Repo.clone_from(git_url, path)
    if version != "latest":
        logger.debug(f"Checking out correct version of repository: {version}")
        repo.git.checkout(version)
    return path


def __build_json_schema(organization: str, action: ActionDefinition) -> str:
    logger.debug(f"Building json schema for '{action.id}'")
    schema = template.replace("{{action-id}}", action.id)
    schema = schema.replace("{{organization}}", organization)
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


def __prepare_actions(file: str, actions: List[Any], parsed: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if parsed is None:
        parsed = {}
    if len(actions) == 0:
        logger.debug("All actions prepared")
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
        if os.path.isdir(action_path):
            logger.debug(f"Action '{act}' is already available, loading from disk")
            with open(os.path.join(action_path, f"{props.name}.schema.json"), "r") as handle:
                json_schema = json.load(handle)
        else:
            logger.debug(f"Action '{act}' is not available on this system")
            # Download the action (clone the repository)
            repo_path = __download_action(props.organization, props.name, props.version)
            # Validate that the action.yml is valid
            action = validate_action_definition(os.path.join(repo_path, "action.yml"))
            # Check if it is a composite action, in that case we might need to retrieve more actions
            if isinstance(action, CompositeActionDefinition):
                logger.debug(f"Action '{act}' is a composite action, preparing sub-actions")
                all_actions: List[Any] = []
                for step in action.steps:
                    name = step.get("uses", None)
                    if name is not None:
                        all_actions.append(step)
                parsed = __prepare_actions(str(repo_path), all_actions, parsed)
            # Now we can build a schema for this action
            schema = __build_json_schema(props.organization, action)
            json_schema = json.loads(schema)
            with open(os.path.join(action_path, f"{props.name}.schema.json"), 'w') as handle:
                handle.write(schema)
            parsed[act] = json_schema
    else:
        json_schema = parsed[act]
    validate_action(file, action_def, json_schema)
    return __prepare_actions(file, actions, parsed)


def prepare_actions(prepare_file: str, steps: Dict[str, Any]) -> None:
    """
    Make sure that the action is available.
    If not available:
    1. Clone the repository
    2. Checkout the correct version
    3. Generate json schema for validation
    :param steps: The actions to prepare
    :param prepare_file
    :return: None
    """
    logger.debug("========== Preparing actions")
    all_actions: List[Any] = []
    # DON'T FORGET TO REMOVE, ONLY FOR DEVELOPMENT
    shutil.rmtree(cache_path, ignore_errors=True)
    # Iterate through all the actions to make sure that they are available
    for step, actions in steps.items():
        for action in actions:
            # If the action is a run command, we don't need to do anything
            if action.get("uses", None) is not None:
                all_actions.append(action)
    __prepare_actions(prepare_file, all_actions)
    logger.debug("✓ All actions downloaded and valid")

