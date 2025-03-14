import json
import os.path
from typing import Dict, Any

from dacite import from_dict
from importlib_resources import files
from pathlib import Path

from jsonschema import validate, ValidationError

from prepare_assignment.data.config import Config
from prepare_assignment.data.constants import YAML_LOADER
from prepare_assignment.data.errors import ValidationError as VE
from prepare_assignment.utils.paths import get_config_path


def __validate_config(config_path: Path, config: Dict[str, Any]) -> None:
    schema_path = files().joinpath('../schemas/config.schema.json')
    schema: Dict[str, Any] = json.loads(schema_path.read_text())

    # Validate config.yml
    try:
        validate(config, schema)
    except ValidationError as ve:
        message = f"Error in config file: {config_path}, unable to verify '{ve.json_path}'\n\t -> {ve.message}"
        raise VE(message)


def load_config() -> None:
    config_path = Path(os.path.join(get_config_path(), "config.yml"))
    if not config_path.is_file():
        return
    yaml = YAML_LOADER.load(config_path)
    # If the file is empty it is still valid config, but validator will fail with None
    if not yaml:
        return
    __validate_config(config_path, yaml)
    config = from_dict(data_class=Config, data=yaml)
