import logging
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Set, List

from git import Repo
from importlib_resources import files

from prepare_assignment.core.validator import validate_action_definition
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


def __download_action(organization: str, action: str, version: str) -> None:
    """
    Download (git) the action and create the json schema
    :param organization: GitHub organization/username
    :param action: action name
    :return: None
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


def __build_json_schema(organization: str, action: ActionDefinition) -> str:
    logger.debug("Building json schema")
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


def __prepare_actions(actions: List[Any], parsed: Dict[str, Any] = None) -> None:
    if len(actions) == 0:
        logger.debug("All actions prepared")
        return
    if parsed is None:
        parsed = set()

    action = actions.pop()
    act: str = action["uses"]
    logger.debug(f"Preparing action: {act}")
    props = __action_properties(act)

    # Check if action (therefore the path) already exists
    action_path = os.path.join(cache_path, props.organization, props.name, props.version)
    if not os.path.isdir(action_path):
        # If not download the action (clone the repository)
        __download_action(props.organization, props.name, props.version)
        repo_path = os.path.join(action_path, "repo")
        # Validate that the action.yml is valid
        action = validate_action_definition(os.path.join(repo_path, "action.yml"))
        # Check if it is a composite action, in that case we might need to retrieve more actions
        if isinstance(action, CompositeActionDefinition):
            logger.debug("Found composite")
        # Now we can build a schema for this action
        schema = __build_json_schema(props.organization, action)
        with open(os.path.join(action_path, f"{props.name}.schema.json"), 'w') as handle:
            handle.write(schema)
    __prepare_actions(actions)


def prepare_actions(steps: Dict[str, Any]) -> None:
    """
    Make sure that the action is available.
    If not available:
    1. Clone the repository
    2. Checkout the correct version
    3. Generate json schema for validation
    :param steps: The actions to prepare
    :return: None
    """
    all_actions: List[Any] = []
    # DON'T FORGET TO REMOVE, ONLY FOR DEVELOPMENT
    shutil.rmtree(cache_path, ignore_errors=True)
    # Iterate through all the actions to make sure that they are available
    for step, actions in steps.items():
        for action in actions:
            # If the action is a run command, we don't need to do anything
            if action.get("uses", None) is not None:
                all_actions.append(action)
    __prepare_actions(all_actions)
    # Validate inputs

