from dataclasses import dataclass, field
from typing import Dict, Any, Optional

from prepare_assignment.data.task_definition import PythonTaskDefinition
from prepare_assignment.data.prepare import Task


@dataclass
class JobEnvironment:
    environment: Dict[str, str]
    outputs: Dict[str, Any]
    inputs: Dict[str, Any]
    job_failed: bool = False
    current_task_definition: Optional[PythonTaskDefinition] = None
    current_task: Optional[Task] = None
