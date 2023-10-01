from typing import Final, Dict, Type

TYPE_MAPPING: Final[Dict[str, Type]] = {
    "string": str,
    "array": list,
    "number": float,
    "integer": int,
    "boolean": bool
}
