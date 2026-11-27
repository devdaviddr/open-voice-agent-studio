from ovas_core.spec import (
    AgentSpec,
    AgentStepData,
    AgentStepNode,
    CelCondition,
    Edge,
    KnowledgeRef,
    Position,
    RouterData,
    RouterNode,
    blank_spec,
)
from ovas_core.templates import receptionist
from ovas_core.validate import validate

P = Position(x=0, y=0)


def codes(spec: AgentSpec, **kw) -> list[str]:
    return sorted(i.code for i in validate(spec, **kw))


def test_templates_are_valid():
    assert validate(blank_spec()) == []
    assert validate(receptionist()) == []


def test_four_problems_reported_against_their_ids():  # MVP AC-7
    spec = blank_spec()
    spec.graph.nodes += [
        AgentStepNode(id="orphan", position=P, data=AgentStepData(label="Orphan")),
        RouterNode(id="router", position=P, data=RouterData(label="R")),
    ]
    spec.graph.edges += [
        Edge(
            id="to-router",
            source="main",
            target="router",
            order=2,
            condition=CelCondition(expr="x >"),
        ),
        Edge(id="router-end", source="router", target="end", condition=CelCondition(expr="x > 1")),
    ]
    spec.graph.nodes[1].data.prompt = "Hello {{x}}"  # type: ignore[union-attr]
    issues = validate(spec)
    by_code = {i.code: i for i in issues}
    assert by_code["unreachable"].node_id == "orphan"
    assert by_code["router_no_else"].node_id == "router"
    assert by_code["bad_cel"].edge_id == "to-router"
    assert by_code["undeclared_variable"].node_id == "main"


def test_missing_start_and_end():
    spec = blank_spec()
    spec.graph.nodes = [n for n in spec.graph.nodes if n.type == "agent_step"]
    spec.graph.edges = []
    assert {"start_count", "no_end"} <= set(codes(spec))


def test_dead_end_node():
    spec = blank_spec()
    spec.graph.edges = [e for e in spec.graph.edges if e.source != "main"]
    assert "dead_end" in codes(spec)


def test_edges_into_start_or_out_of_end_rejected():
    spec = blank_spec()
    spec.graph.edges.append(Edge(id="bad", source="end", target="start"))
    assert "invalid_edge" in codes(spec)


def test_extract_outputs_must_be_declared():
    spec = receptionist()
    spec.variables = [v for v in spec.variables if v.name != "caller.phone"]
    issues = [i for i in validate(spec) if i.code == "undeclared_variable"]
    assert {i.node_id for i in issues} >= {"collect", "emergency"}


def test_deleted_knowledge_source_flagged():
    spec = receptionist()
    spec.knowledge = [KnowledgeRef(source_id="gone")]
    assert "missing_knowledge" in codes(spec, knowledge_ids=["other"])
    assert "missing_knowledge" not in codes(spec, knowledge_ids=["gone"])
