"""The complete voice catalog must describe executable business arguments."""

import copy

from desk.assistant import TOOLS
from desk.voice_protocols import flatten_schema


def test_complete_voice_catalog_keeps_required_business_properties():
    def check(schema, path):
        if isinstance(schema, dict):
            if schema.get("type") == "object":
                assert set(schema.get("required", [])) <= set(schema.get("properties", {})), path
            for key, value in schema.items():
                check(value, path + "." + key)
        elif isinstance(schema, list):
            for index, value in enumerate(schema):
                check(value, f"{path}[{index}]")

    for tool in TOOLS:
        check(flatten_schema(tool["parameters"]), tool["name"])
    event = next(tool for tool in TOOLS if tool["name"] == "calendar_create_draft")
    assert "title" in flatten_schema(event["parameters"])["properties"]["event"]["properties"]


def test_schema_annotations_do_not_remove_property_names_or_literal_values():
    schema = {
        "title": "Schema annotation",
        "type": "object",
        "properties": {
            "title": {"type": "string", "title": "Field annotation"},
            "default": {"type": "string", "default": "Unused default"},
            "choice": {"const": {"title": "Business value", "default": True}},
        },
        "required": ["title", "default"],
    }
    before = copy.deepcopy(schema)
    flattened = flatten_schema(schema)
    assert "title" not in flattened
    assert flattened["properties"]["title"] == {"type": "string"}
    assert flattened["properties"]["default"] == {"type": "string"}
    assert flattened["properties"]["choice"] == schema["properties"]["choice"]
    assert schema == before
