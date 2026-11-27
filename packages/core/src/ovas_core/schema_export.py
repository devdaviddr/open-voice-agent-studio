"""Export AgentSpec as JSON Schema for TypeScript codegen. Run via `make gen`."""

import json
import sys
from pathlib import Path

from ovas_core.spec import AgentSpec


def _strip_property_titles(node: object) -> None:
    """Drop per-property titles (json2ts makes an alias of each); keep model titles."""
    if isinstance(node, dict):
        for prop in node.get("properties", {}).values():
            prop.pop("title", None)
        for value in node.values():
            _strip_property_titles(value)
    elif isinstance(node, list):
        for item in node:
            _strip_property_titles(item)


def export(path: Path) -> None:
    schema = AgentSpec.model_json_schema(mode="serialization")
    _strip_property_titles(schema)
    schema["title"] = "AgentSpec"
    path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    export(Path(sys.argv[1]))
