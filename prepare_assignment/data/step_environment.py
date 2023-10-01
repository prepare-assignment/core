from dataclasses import dataclass
from typing import Dict, Any, Optional

from prepare_assignment.data.action_definition import PythonActionDefinition
from prepare_assignment.data.prepare import Action


@dataclass
class StepEnvironment:
    environment: Dict[str, str]
    output: Dict[str, Any]
    current_action_definition: Optional[PythonActionDefinition] = None
    current_action: Optional[Action] = None
