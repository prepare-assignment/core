import pytest

from prepare_assignment.utils.resources import load_schema


@pytest.mark.parametrize("name", ["prepare.schema.json", "task.schema.json", "config.schema.json"])
def test_load_schema(name: str) -> None:
    schema = load_schema(name)
    assert schema["$schema"].startswith("http://json-schema.org/")


def test_load_missing_schema() -> None:
    with pytest.raises(FileNotFoundError):
        load_schema("missing.schema.json")
