from ovas_core.diff import diff
from ovas_core.templates import receptionist


def test_identical_specs_have_no_changes():
    assert diff(receptionist(), receptionist()) == []


def test_prompt_change_and_removed_edge_are_exactly_two_changes():  # MVP AC-11
    before = receptionist()
    after = receptionist()
    triage = next(n for n in after.graph.nodes if n.id == "triage")
    triage.data.prompt += "\nAlways ask for the caller's name first."  # type: ignore[union-attr]
    after.graph.edges = [e for e in after.graph.edges if e.id != "e-bye"]
    changes = diff(before, after)
    assert [(c.kind, c.change, c.id) for c in changes] == [
        ("node", "changed", "triage"),
        ("edge", "removed", "e-bye"),
    ]
    prompt = changes[0].fields[0]
    assert prompt.path == "data.prompt"
    assert "+ Always ask for the caller's name first." in (prompt.lines or [])
    assert changes[1].label == "Triage → Goodbye"


def test_moving_a_node_is_not_a_change():
    after = receptionist()
    after.graph.nodes[0].position.x += 100
    assert diff(receptionist(), after) == []


def test_settings_and_variables():
    after = receptionist()
    after.settings.llm.temperature = 0.2
    after.variables = after.variables[1:]
    kinds = {(c.kind, c.change) for c in diff(receptionist(), after)}
    assert kinds == {("setting", "changed"), ("variable", "removed")}
