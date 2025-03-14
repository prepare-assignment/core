import json
import os.path
from enum import Enum
from typing import Dict, Any

import dacite
from dacite import from_dict
from importlib_resources import files
from pathlib import Path

from jsonschema import validate, ValidationError

from prepare_assignment.data.config import Config, Core
from prepare_assignment.data.errors import ValidationError as VE
from prepare_assignment.utils.paths import get_config_path
from prepare_assignment.utils.yml_loader import YAML_LOADER


def __convert_keys(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k.replace("-", "_"): __convert_keys(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [__convert_keys(i) for i in obj]
    return obj


def __validate_config(config_path: Path, config: Dict[str, Any]) -> None:
    schema_path = files().joinpath('../schemas/config.schema.json')
    schema: Dict[str, Any] = json.loads(schema_path.read_text())

    # Validate config.yml
    try:
        validate(config, schema)
    except ValidationError as ve:
        message = f"Error in config file: {config_path}, unable to verify '{ve.json_path}'\n\t -> {ve.message}"
        raise VE(message)


def load_config() -> Config:
    config_path = Path(os.path.join(get_config_path(), "config.yml"))
    config = Config(Core())
    if not config_path.is_file():
        return config
    yaml = YAML_LOADER.load(config_path)
    # If the file is empty it is still valid config, but validator will fail with None
    if not yaml:
        return config

    __validate_config(config_path, yaml)
    converted_yaml = __convert_keys(yaml)
    config = from_dict(
        data_class=Config,
        data=converted_yaml,
        config=dacite.Config(cast=[Enum])
    )
    return config
