import json
from importlib.resources import files
from typing import Any, Dict


def load_schema(name: str) -> Dict[str, Any]:
    """
    Load one of the bundled json schemas

    :param name: file name of the schema, e.g. 'prepare.schema.json'
    :return: the parsed schema
    """
    schema: Dict[str, Any] = json.loads(files("prepare_assignment").joinpath("schemas", name).read_text())
    return schema
