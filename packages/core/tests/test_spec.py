import pytest
from pydantic import ValidationError

from ovas_core.spec import AgentSpec, blank_spec

ALL_NODES = {
    "schema_version": "1",
    "graph": {
        "nodes": [
            {"id": "s", "type": "start", "position": {"x": 0, "y": 0}, "data": {"set": {"n": "1"}}},
            {"id": "a", "type": "agent_step", "position": {"x": 1, "y": 0}, "data": {"label": "A"}},
            {"id": "x", "type": "extract", "position": {"x": 2, "y": 0}, "data": {"label": "X"}},
            {"id": "r", "type": "router", "position": {"x": 3, "y": 0}, "data": {"label": "R"}},
            {
                "id": "t",
                "type": "tool_call",
                "position": {"x": 4, "y": 0},
                "data": {"label": "T", "tool": {"kind": "builtin", "name": "end_session"}},
            },
            {
                "id": "h",
                "type": "handoff",
                "position": {"x": 5, "y": 0},
                "data": {"label": "H", "agent_id": "other"},
            },
            {"id": "e", "type": "end", "position": {"x": 6, "y": 0}, "data": {"outcome": "done"}},
            {"id": "n", "type": "note", "position": {"x": 7, "y": 0}, "data": {"text": "hi"}},
        ],
        "edges": [
            {"id": "1", "source": "s", "target": "a"},
            {"id": "2", "source": "a", "target": "r", "condition": {"kind": "llm", "text": "ok"}},
            {
                "id": "3",
                "source": "r",
                "target": "e",
                "condition": {"kind": "cel", "expr": "n > 0"},
            },
            {"id": "4", "source": "r", "target": "x", "condition": {"kind": "else"}},
        ],
    },
}


def test_round_trip_every_node_type():  # M0 AC-6
    spec = AgentSpec.model_validate(ALL_NODES)
    again = AgentSpec.model_validate(spec.model_dump(mode="json"))
    assert again == spec
    assert [n.type for n in spec.graph.nodes] == [
        "start",
        "agent_step",
        "extract",
        "router",
        "tool_call",
        "handoff",
        "end",
        "note",
    ]


def test_unknown_node_type_rejected():
    bad = {"graph": {"nodes": [{"id": "z", "type": "teleport", "position": {"x": 0, "y": 0}}]}}
    with pytest.raises(ValidationError):
        AgentSpec.model_validate(bad)


def test_unknown_field_rejected():
    with pytest.raises(ValidationError):
        AgentSpec.model_validate({"settings": {"promt": "typo"}})


def test_variable_names_are_dotted_snake_case():
    AgentSpec.model_validate({"variables": [{"name": "caller.name"}]})
    with pytest.raises(ValidationError):
        AgentSpec.model_validate({"variables": [{"name": "Caller Name"}]})


def test_blank_spec_is_valid_and_connected():
    spec = blank_spec()
    assert {n.type for n in spec.graph.nodes} == {"start", "agent_step", "end"}
    assert len(spec.graph.edges) == 2
