from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, List, TypedDict

from prepare_assignment.data.task_properties import TaskProperties


@dataclass
class TaskInputDefinition:
    name: str
    description: str
    required: bool
    type: str
    default: str | List[Any] | bool | int | float | None = None
    items: Optional[str] = None

    @classmethod
    def of(cls, name: str, yaml: Dict[str, Any]) -> TaskInputDefinition:
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

    def __str__(self) -> str:
        output = [
            f"name: {self.name}",
            f"description: {self.description}",
            f"required: {self.required}",
            f"type: {self.type}"
        ]
        if self.items is not None:
            output.append(f"items: {self.items}")
        if self.default is not None:
            output.append(f"default: {self.default}")
        return os.linesep.join(output)


@dataclass
class TaskOutputDefinition:
    description: str
    type: str
    items: Optional[str]

    @classmethod
    def of(cls, yaml: Dict[str, Any]) -> TaskOutputDefinition:
        items = yaml.get("items", None)
        return cls(
            description=yaml["description"],
            type=yaml["type"],
            items=items
        )

    def __str__(self) -> str:
        output = [
            f"description: {self.description}",
            f"type: {self.type}"
        ]
        if self.items is not None:
            output.append(f"items: {self.items}")
        return os.linesep.join(output)


@dataclass
class TaskDefinition(ABC):
    id: str
    name: str
    description: str
    inputs: List[TaskInputDefinition]
    outputs: Dict[str, TaskOutputDefinition]
    path: Path

    @property
    @abstractmethod
    def is_composite(self) -> bool:
        ...

    @staticmethod
    def _dict_to_inputs(dictionary: Dict[str, Any]) -> List[TaskInputDefinition]:
        return [TaskInputDefinition.of(key, value) for key, value in dictionary.items()]

    @staticmethod
    def _yaml_to_outputs(yaml: Dict[str, Any]) -> Dict[str, TaskOutputDefinition]:
        return {key: TaskOutputDefinition.of(value) for key, value in yaml.items()}

    @staticmethod
    def of(yaml: Dict[str, Any], path: Path) -> TaskDefinition:
        if yaml["runs"]["using"] == "composite":
            return CompositeTaskDefinition.of(yaml, path)
        else:
            return PythonTaskDefinition.of(yaml, path)

    def __str__(self) -> str:
        output = [f"id: {self.id}", f"name: {self.name}", f"description: {self.description}"]
        if len(self.inputs) > 0:
            inputs = ["inputs:"]
            for inp in self.inputs:
                input_string = "\n    ".join(str(inp).split(os.linesep))
                inputs.append(f"  - {input_string}")
            output.append(os.linesep.join(inputs))
        if len(self.outputs) > 0:
            outputs = ["outputs:"]
            for key, definition in self.outputs.items():
                output_string = f"{key}{os.linesep}    "
                output_string += "\n    ".join(str(definition).split(os.linesep))
                outputs.append(f"  {str(output_string)}")
            output.append(os.linesep.join(outputs))
        return os.linesep.join(output)


@dataclass
class PythonTaskDefinition(TaskDefinition):
    main: str

    @classmethod
    def of(cls, yaml: Dict[str, Any], path: Path) -> PythonTaskDefinition:
        inputs = yaml.get("inputs", {})
        outputs = yaml.get("outputs", {})
        return cls(
            id=yaml["id"],
            name=yaml["name"],
            description=yaml["description"],
            inputs=TaskDefinition._dict_to_inputs(inputs),
            outputs=TaskDefinition._yaml_to_outputs(outputs),
            main=yaml["runs"]["main"],
            path=path
        )

    @property
    def is_composite(self) -> bool:
        return False


@dataclass
class CompositeTaskDefinition(TaskDefinition):
    tasks: List[Any]

    @classmethod
    def of(cls, yaml: Dict[str, Any], path: Path) -> CompositeTaskDefinition:
        inputs = yaml.get("inputs", {})
        outputs = yaml.get("outputs", {})
        return cls(
            id=yaml["id"],
            name=yaml["name"],
            description=yaml["description"],
            tasks=yaml["runs"]["tasks"],
            inputs=TaskDefinition._dict_to_inputs(inputs),
            outputs=TaskDefinition._yaml_to_outputs(outputs),
            path=path
        )

    @property
    def is_composite(self) -> bool:
        return True


class ValidableTask(TypedDict):
    schema: Any
    task: TaskDefinition
