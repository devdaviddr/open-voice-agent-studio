"""Structural diff between two agent specs (MVP FR-12). Node positions are layout and ignored."""

import difflib
from typing import Any, Literal

from pydantic import BaseModel

from ovas_core.spec import AgentSpec

TEXT_FIELDS = {"prompt", "first_message", "instructions", "message", "text"}


class FieldChange(BaseModel):
    path: str
    before: Any = None
    after: Any = None
    lines: list[str] | None = None  # line diff for long text: "+ added", "- removed", "  same"


class Change(BaseModel):
    kind: Literal["node", "edge", "setting", "variable", "other"]
    change: Literal["added", "removed", "changed"]
    id: str
    label: str
    fields: list[FieldChange] = []


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            out |= _flatten(v, f"{prefix}.{k}" if prefix else k)
        return out
    return {prefix: value}


def _fields(before: dict, after: dict) -> list[FieldChange]:
    a, b = _flatten(before), _flatten(after)
    changes = []
    for path in sorted(a.keys() | b.keys()):
        if a.get(path) == b.get(path):
            continue
        fc = FieldChange(path=path, before=a.get(path), after=b.get(path))
        leaf = path.rsplit(".", 1)[-1]
        if (
            leaf in TEXT_FIELDS
            and isinstance(fc.before or "", str)
            and isinstance(fc.after or "", str)
        ):
            fc.lines = [
                line
                for line in difflib.ndiff(
                    (fc.before or "").splitlines(), (fc.after or "").splitlines()
                )
                if not line.startswith("?")
            ]
        changes.append(fc)
    return changes


def _label(node: dict) -> str:
    data = node.get("data", {})
    return data.get("label") or data.get("text", "")[:40] or node["type"]


def diff(before: AgentSpec, after: AgentSpec) -> list[Change]:
    b = before.model_dump(mode="json")
    a = after.model_dump(mode="json")
    changes: list[Change] = []

    b_nodes = {n["id"]: n for n in b["graph"]["nodes"]}
    a_nodes = {n["id"]: n for n in a["graph"]["nodes"]}
    for node_id in sorted(b_nodes.keys() | a_nodes.keys()):
        old, new = b_nodes.get(node_id), a_nodes.get(node_id)
        if old is None and new is not None:
            changes.append(Change(kind="node", change="added", id=node_id, label=_label(new)))
        elif new is None and old is not None:
            changes.append(Change(kind="node", change="removed", id=node_id, label=_label(old)))
        elif old and new:
            fields = _fields(
                {"type": old["type"], "data": old["data"]},
                {"type": new["type"], "data": new["data"]},
            )
            if fields:
                changes.append(
                    Change(
                        kind="node", change="changed", id=node_id, label=_label(new), fields=fields
                    )
                )

    def edge_label(e: dict, nodes: dict) -> str:
        name = lambda i: _label(nodes[i]) if i in nodes else i  # noqa: E731
        return f"{name(e['source'])} → {name(e['target'])}"

    b_edges = {e["id"]: e for e in b["graph"]["edges"]}
    a_edges = {e["id"]: e for e in a["graph"]["edges"]}
    for edge_id in sorted(b_edges.keys() | a_edges.keys()):
        old, new = b_edges.get(edge_id), a_edges.get(edge_id)
        if old is None and new is not None:
            changes.append(
                Change(kind="edge", change="added", id=edge_id, label=edge_label(new, a_nodes))
            )
        elif new is None and old is not None:
            changes.append(
                Change(kind="edge", change="removed", id=edge_id, label=edge_label(old, b_nodes))
            )
        elif old and new and old != new:
            changes.append(
                Change(
                    kind="edge",
                    change="changed",
                    id=edge_id,
                    label=edge_label(new, a_nodes),
                    fields=_fields(old, new),
                )
            )

    settings = _fields(b["settings"], a["settings"])
    if settings:
        changes.append(
            Change(
                kind="setting",
                change="changed",
                id="settings",
                label="Agent settings",
                fields=settings,
            )
        )

    b_vars = {v["name"]: v for v in b["variables"]}
    a_vars = {v["name"]: v for v in a["variables"]}
    for name in sorted(b_vars.keys() | a_vars.keys()):
        old, new = b_vars.get(name), a_vars.get(name)
        if old is None:
            changes.append(Change(kind="variable", change="added", id=name, label=name))
        elif new is None:
            changes.append(Change(kind="variable", change="removed", id=name, label=name))
        elif old != new:
            changes.append(
                Change(
                    kind="variable", change="changed", id=name, label=name, fields=_fields(old, new)
                )
            )

    for key in ("tools", "knowledge", "pronunciation", "memory", "recording"):
        if b[key] != a[key]:
            changes.append(
                Change(
                    kind="other",
                    change="changed",
                    id=key,
                    label=key.capitalize(),
                    fields=[FieldChange(path=key, before=b[key], after=a[key])],
                )
            )
    return changes
