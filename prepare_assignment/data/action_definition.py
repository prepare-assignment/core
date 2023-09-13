from __future__ import annotations

import json
from abc import ABC
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, List, TypedDict


@dataclass
class PythonActionDefinitionInput:
    name: str
    description: str
    required: bool
    type: str
    default: Optional[str] | Optional[List[Any]] = None
    items: Optional[str] = None

    @classmethod
    def of(cls, name: str, yaml: Dict[str, Any]) -> PythonActionDefinitionInput:
        default = yaml.get("default", None)
        items = yaml.get("items", None)
        return cls(
            name=name,
            description=yaml["description"],
            required=yaml["required"],
            type=yaml["type"],
            default=default,
            items=items
        )

    def to_schema_definition(self) -> str:

        properties = [f'"type": "{self.type}"']
        if self.type == "array":
            properties.append(f'"items": {{ "type": "{self.items}" }}')
        if self.default is not None:
            properties.append(f'"default": {json.dumps(self.default)}')
        joined = ",\n  ".join(properties)
        return f'"{self.name}": {{\n  {joined}\n}}'


@dataclass
class ActionDefinition(ABC):
    id: str
    name: str
    description: str
    inputs: List[PythonActionDefinitionInput]
    path: str

    @staticmethod
    def _dict_to_inputs(dictionary: Dict[str, Any]) -> List[PythonActionDefinitionInput]:
        return [PythonActionDefinitionInput.of(key, value) for key, value in dictionary.items()]


@dataclass
class PythonActionDefinition(ActionDefinition):
    main: str

    @classmethod
    def of(cls, yaml: Dict[str, Any], path: str) -> PythonActionDefinition:
        inputs = yaml.get("inputs", {})
        return cls(
            id=yaml["id"],
            name=yaml["name"],
            description=yaml["description"],
            inputs=ActionDefinition._dict_to_inputs(inputs),
            main=yaml["runs"]["main"],
            path=path
        )


@dataclass
class CompositeActionDefinition(ActionDefinition):
    steps: List[Any]

    @classmethod
    def of(cls, yaml: Dict[str, Any], path: str) -> CompositeActionDefinition:
        inputs = yaml.get("inputs", {})
        return cls(
            id=yaml["id"],
            name=yaml["name"],
            description=yaml["description"],
            steps=yaml["runs"]["steps"],
            inputs=ActionDefinition._dict_to_inputs(inputs),
            path=path
        )
