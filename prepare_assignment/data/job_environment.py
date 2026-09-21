from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

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
    # Errors reported by the currently executing step (via 'set-failed' or malformed commands)
    task_errors: List[str] = field(default_factory=list)
    # Environment variables that only apply to the current step (the 'env' of a step), these are
    # not persisted in 'environment', which is shared between steps
    env_overlay: Dict[str, str] = field(default_factory=dict)
    # Working directory for the current step, None means the current working directory
    working_directory: Optional[str] = None

    @property
    def process_environment(self) -> Dict[str, str]:
        return {**self.environment, **self.env_overlay}
