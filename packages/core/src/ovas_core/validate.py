"""Graph validation (MVP FR-8). Problems block publishing; the builder shows them on the canvas."""

import re
from collections import defaultdict, deque
from collections.abc import Iterable
from typing import Literal

import celpy
from pydantic import BaseModel

from ovas_core.spec import (
    AgentSpec,
    AgentStepNode,
    CelCondition,
    ElseCondition,
    EndNode,
    ExtractNode,
    NoteNode,
    RouterNode,
    StartNode,
)

TEMPLATE_VAR = re.compile(r"\{\{\s*([^{}]*?)\s*\}\}")
# Node types the MVP engine can run (spec/mvp FR-6); tool_call and handoff arrive in M3.
SUPPORTED = {"start", "agent_step", "extract", "router", "end", "note"}
_cel = celpy.Environment()


class Issue(BaseModel):
    code: str
    message: str
    severity: Literal["error", "warning"] = "error"
    node_id: str | None = None
    edge_id: str | None = None


def template_vars(text: str) -> list[str]:
    return TEMPLATE_VAR.findall(text or "")


def cel_error(expr: str) -> str | None:
    try:
        _cel.compile(expr)
    except Exception as e:  # celpy raises several parse/compile error types
        first = str(e).strip().splitlines()[0] if str(e).strip() else type(e).__name__
        return first
    return None


def validate(spec: AgentSpec, knowledge_ids: Iterable[str] | None = None) -> list[Issue]:
    issues: list[Issue] = []
    nodes = {n.id: n for n in spec.graph.nodes}
    flow_nodes = {i: n for i, n in nodes.items() if not isinstance(n, NoteNode)}
    out: dict[str, list] = defaultdict(list)
    incoming: dict[str, list] = defaultdict(list)

    if len(nodes) != len(spec.graph.nodes):
        issues.append(Issue(code="duplicate_id", message="Two nodes share an ID."))

    for node in spec.graph.nodes:
        if node.type not in SUPPORTED:
            issues.append(
                Issue(
                    code="unsupported_node",
                    message=f"{node.type.replace('_', ' ').title()} nodes are not available yet.",
                    node_id=node.id,
                )
            )

    for edge in spec.graph.edges:
        if edge.source not in nodes or edge.target not in nodes:
            issues.append(
                Issue(
                    code="dangling_edge", message="Edge points at a missing node.", edge_id=edge.id
                )
            )
            continue
        if isinstance(nodes[edge.source], (NoteNode, EndNode)) or isinstance(
            nodes[edge.target], (NoteNode, StartNode)
        ):
            issues.append(
                Issue(
                    code="invalid_edge", message="This connection is not allowed.", edge_id=edge.id
                )
            )
            continue
        out[edge.source].append(edge)
        incoming[edge.target].append(edge)
        if isinstance(edge.condition, CelCondition) and (err := cel_error(edge.condition.expr)):
            issues.append(
                Issue(code="bad_cel", message=f"Expression does not parse: {err}", edge_id=edge.id)
            )

    starts = [n for n in spec.graph.nodes if isinstance(n, StartNode)]
    if len(starts) != 1:
        issues.append(
            Issue(code="start_count", message="The workflow needs exactly one Start node.")
        )
    if not any(isinstance(n, EndNode) for n in spec.graph.nodes):
        issues.append(Issue(code="no_end", message="Add an End node so conversations can finish."))

    # Reachability from Start, and every reachable node able to reach an End.
    if starts:
        reached = _walk(starts[0].id, lambda n: (e.target for e in out[n]))
        for node_id in flow_nodes.keys() - reached:
            issues.append(
                Issue(
                    code="unreachable",
                    message="No path from Start reaches this node.",
                    node_id=node_id,
                )
            )
        ends = [i for i, n in flow_nodes.items() if isinstance(n, EndNode)]
        can_finish: set[str] = set()
        for end in ends:
            can_finish |= _walk(end, lambda n: (e.source for e in incoming[n]))
        for node_id in reached - can_finish:
            if not out[node_id]:
                issues.append(
                    Issue(
                        code="dead_end",
                        message="Connect this node to the next step.",
                        node_id=node_id,
                    )
                )
            else:
                issues.append(
                    Issue(
                        code="no_path_to_end",
                        message="No path from here reaches an End node.",
                        node_id=node_id,
                    )
                )

    for node in spec.graph.nodes:
        edges = out[node.id]
        if isinstance(node, RouterNode) and not any(
            isinstance(e.condition, ElseCondition) for e in edges
        ):
            issues.append(
                Issue(
                    code="router_no_else",
                    message="Add an 'else' edge so the router always has somewhere to go.",
                    node_id=node.id,
                )
            )
        if sum(isinstance(e.condition, ElseCondition) for e in edges) > 1:
            issues.append(
                Issue(
                    code="multiple_else",
                    message="Only one 'else' edge is allowed.",
                    node_id=node.id,
                )
            )
        if isinstance(node, RouterNode) and any(e.condition is None for e in edges):
            issues.append(
                Issue(
                    code="router_unconditional",
                    message="Router edges need a condition or 'else'.",
                    node_id=node.id,
                )
            )

    issues += _variable_issues(spec)

    if knowledge_ids is not None:
        known = set(knowledge_ids)
        refs = [(None, r.source_id) for r in spec.knowledge]
        refs += [
            (n.id, r.source_id)
            for n in spec.graph.nodes
            if isinstance(n, AgentStepNode)
            for r in (n.data.knowledge or [])
        ]
        for node_id, source_id in refs:
            if source_id not in known:
                issues.append(
                    Issue(
                        code="missing_knowledge",
                        message="A knowledge source this agent uses has been deleted.",
                        node_id=node_id,
                    )
                )
    return issues


def _variable_issues(spec: AgentSpec) -> list[Issue]:
    issues: list[Issue] = []
    declared = {v.name for v in spec.variables}
    names = [v.name for v in spec.variables]
    for dup in {n for n in names if names.count(n) > 1}:
        issues.append(
            Issue(code="duplicate_variable", message=f"Variable '{dup}' is declared twice.")
        )
    for v in spec.variables:
        if v.type == "enum" and not v.enum:
            issues.append(
                Issue(code="enum_no_values", message=f"Enum variable '{v.name}' needs values.")
            )

    def check(text: str | None, node_id: str | None) -> None:
        for name in template_vars(text or ""):
            if name not in declared:
                issues.append(
                    Issue(
                        code="undeclared_variable",
                        message=f"'{{{{{name}}}}}' is not a declared variable.",
                        node_id=node_id,
                    )
                )

    check(spec.settings.prompt, None)
    check(spec.settings.first_message, None)
    for node in spec.graph.nodes:
        if isinstance(node, AgentStepNode):
            check(node.data.prompt, node.id)
        elif isinstance(node, StartNode):
            check(node.data.first_message, node.id)
            for name in node.data.set:
                if name not in declared:
                    issues.append(
                        Issue(
                            code="undeclared_variable",
                            message=f"Start sets '{name}', which is not declared.",
                            node_id=node.id,
                        )
                    )
        elif isinstance(node, EndNode):
            check(node.data.message, node.id)
        elif isinstance(node, ExtractNode):
            check(node.data.instructions, node.id)
            if not node.data.outputs:
                issues.append(
                    Issue(
                        code="extract_empty", message="Choose variables to fill.", node_id=node.id
                    )
                )
            for name in node.data.outputs:
                if name not in declared:
                    issues.append(
                        Issue(
                            code="undeclared_variable",
                            message=f"'{name}' is not a declared variable.",
                            node_id=node.id,
                        )
                    )
    return issues


def _walk(start: str, neighbours) -> set[str]:
    seen = {start}
    queue = deque([start])
    while queue:
        for nxt in neighbours(queue.popleft()):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return seen
