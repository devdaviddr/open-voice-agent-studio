"""The workflow engine: runs an AgentSpec as a text conversation (MVP FR-9, FR-13, FR-14, FR-17).

Pure orchestration. The LLM, knowledge search and memory recall are injected, so the engine runs
the same in the runtime, in tests (with a scripted fake LLM) and later in the voice pipeline.

Turn semantics: when the caller speaks, the current node's outgoing edges are checked first (CEL
expressions, then one batched model judgement, then `else`). If one fires, the session moves on,
passing through Router and Extract nodes, and the node it lands on replies. Otherwise the current
node replies. Unconditional edges from an Agent step fire once the step has replied at least once.
"""

import contextlib
import json
import re
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol

import celpy
from celpy.adapter import json_to_cel

from ovas_core.spec import (
    AgentSpec,
    AgentStepNode,
    CelCondition,
    Edge,
    ElseCondition,
    EndNode,
    ExtractNode,
    LlmCondition,
    NoteNode,
    RouterNode,
    StartNode,
    VariableDef,
    VoiceSettings,
)
from ovas_core.validate import TEMPLATE_VAR

MAX_HOPS = 10
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# --- injected services ---------------------------------------------------------------------------


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LlmChunk:
    """One streamed piece of a reply: text, or a complete tool call."""

    text: str = ""
    tool_call: ToolCall | None = None


class Llm(Protocol):
    def stream(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None,
        temperature: float,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[LlmChunk]: ...

    async def json(
        self, messages: list[dict[str, Any]], *, model: str | None, schema: dict[str, Any]
    ) -> dict[str, Any]: ...


Emit = Callable[[str, dict[str, Any]], Awaitable[None]]
KnowledgeSearch = Callable[[str, list[str] | None, int], Awaitable[list[dict[str, Any]]]]
MemoryRecall = Callable[[str, int], Awaitable[list[str]]]


# --- helpers -------------------------------------------------------------------------------------


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def get_var(store: dict[str, Any], name: str) -> Any:
    value: Any = store
    for part in name.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def set_var(store: dict[str, Any], name: str, value: Any) -> None:
    parts = name.split(".")
    target = store
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = value


def render(text: str | None, variables: dict[str, Any]) -> str:
    def sub(m: re.Match[str]) -> str:
        value = get_var(variables, m.group(1))
        return "" if value is None else str(value)

    return TEMPLATE_VAR.sub(sub, text or "")


def coerce(var: VariableDef, value: Any) -> Any:
    """Validate an extracted value against its declared type; ValueError if it does not fit."""
    if value is None or value == "":
        raise ValueError("empty")
    match var.type:
        case "string":
            return str(value)
        case "number":
            if isinstance(value, bool):
                raise ValueError("not a number")
            return float(value) if "." in str(value) else int(value)
        case "boolean":
            if isinstance(value, bool):
                return value
            if str(value).lower() in {"true", "yes"}:
                return True
            if str(value).lower() in {"false", "no"}:
                return False
            raise ValueError("not a boolean")
        case "date":
            return date.fromisoformat(str(value)).isoformat()
        case "email":
            if not EMAIL.match(str(value)):
                raise ValueError("not an email address")
            return str(value)
        case "enum":
            if str(value) not in (var.enum or []):
                raise ValueError("not an allowed value")
            return str(value)
        case "object":
            if not isinstance(value, dict):
                raise ValueError("not an object")
            return value
    raise ValueError(f"unknown type {var.type}")


_cel_env = celpy.Environment()


def cel_true(expr: str, variables: dict[str, Any]) -> bool:
    """Evaluate a CEL condition; any error (missing variable, wrong type) counts as false."""
    try:
        program = _cel_env.program(_cel_env.compile(expr))
        activation = {k: json_to_cel(v) for k, v in variables.items()}
        return bool(program.evaluate(activation))  # type: ignore[arg-type]
    except Exception:
        return False


def _json_type(var: VariableDef) -> dict[str, Any]:
    """Extraction field schema. Every field is a string and "" means "not given": with nullable
    fields, constrained decoding on small local models picks null almost every time. coerce()
    then turns the text into the declared type."""
    hint = {
        "number": "a number",
        "boolean": "true or false",
        "date": "a date as YYYY-MM-DD",
        "email": "an email address",
        "object": "a JSON object",
    }.get(var.type, "text")
    t: dict[str, Any] = {
        "type": "string",
        "description": f"{var.description or var.name} ({hint}), or an empty string if not given",
    }
    if var.type == "enum":
        t["enum"] = [*(var.enum or []), ""]
    return t


BUILTIN_TOOLS: dict[str, dict[str, Any]] = {
    "end_session": {
        "description": "End the conversation once the caller is done and has said goodbye.",
        "parameters": {"type": "object", "properties": {}},
    },
    "search_knowledge": {
        "description": "Search the knowledge base for facts (hours, prices, policies) "
        "before answering.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "What to look up"}},
            "required": ["query"],
        },
    },
    "recall_memory": {
        "description": "Search what you remember about this caller from earlier conversations.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
}


# --- the session ---------------------------------------------------------------------------------


@dataclass
class TextSession:
    spec: AgentSpec
    llm: Llm
    emit: Emit
    default_model: str | None = None
    variables: dict[str, Any] = field(default_factory=dict)
    search_knowledge: KnowledgeSearch | None = None
    recall_memory: MemoryRecall | None = None
    recalled: list[str] = field(default_factory=list)

    history: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    current: str = ""
    replies_in_node: int = 0
    ended: bool = False
    outcome: str | None = None
    usage: dict[str, int] = field(default_factory=lambda: {"llm_calls": 0, "turns": 0})

    def __post_init__(self) -> None:
        self.nodes = {n.id: n for n in self.spec.graph.nodes if not isinstance(n, NoteNode)}
        self.out: dict[str, list[Edge]] = {}
        for edge in sorted(self.spec.graph.edges, key=lambda e: e.order):
            self.out.setdefault(edge.source, []).append(edge)
        self.declared = {v.name: v for v in self.spec.variables}

    # public API ---------------------------------------------------------------------------------

    async def start(self) -> None:
        start = next(n for n in self.nodes.values() if isinstance(n, StartNode))
        await self._enter(start.id)
        for name, expr in start.data.set.items():
            await self._set_variable(name, self._cel_value(expr))
        if self.recall_memory and self.spec.memory.enabled:
            self.recalled = await self.recall_memory("", 5)
            await self.emit("memory", {"recalled": [{"fact": f} for f in self.recalled]})
        text = render(start.data.first_message or self.spec.settings.first_message, self.variables)
        if text:
            await self._say(text, voice=self.spec.settings.voice)
        await self._advance(start.id)

    async def user_message(self, text: str) -> None:
        if self.ended:
            await self.emit("error", {"message": "The session has ended."})
            return
        self.usage["turns"] += 1
        self.history.append({"role": "user", "content": text})
        await self._compact_history()
        node = self.nodes[self.current]
        if isinstance(node, ExtractNode):
            await self._run_extract(node)
            return
        moved = await self._take_edge(node)
        if moved:
            await self._advance(moved)
        else:
            await self._respond()

    async def end(self, outcome: str = "hung_up") -> None:
        if not self.ended:
            self.ended = True
            self.outcome = outcome
            await self.emit("ended", {"outcome": outcome})

    # movement -----------------------------------------------------------------------------------

    async def _enter(self, node_id: str) -> None:
        self.current = node_id
        self.replies_in_node = 0
        await self.emit("node_enter", {"node_id": node_id})

    async def _advance(self, node_id: str, hops: int = 0) -> None:
        """Move into node_id (or onward from it when it is Start) and do what that node does."""
        if hops > MAX_HOPS:
            await self.emit("error", {"message": "The workflow loops without speaking; stopping."})
            await self.end("error")
            return
        node = self.nodes[node_id]
        if isinstance(node, StartNode):
            nxt = await self._take_edge(node)
            if nxt:
                await self._advance(nxt, hops + 1)
            return
        if node_id != self.current:
            await self._enter(node_id)
        if isinstance(node, RouterNode):
            nxt = await self._take_edge(node)
            if nxt is None:
                await self.emit(
                    "error", {"message": f"Router '{node.data.label}' had nowhere to go."}
                )
                await self.end("error")
            else:
                await self._advance(nxt, hops + 1)
        elif isinstance(node, ExtractNode):
            await self._run_extract(node, hops)
        elif isinstance(node, EndNode):
            if node.data.message:
                await self._say(
                    render(node.data.message, self.variables), voice=self.spec.settings.voice
                )
            await self.end(node.data.outcome)
        elif (
            isinstance(node, AgentStepNode) and self.history and self.history[-1]["role"] == "user"
        ):
            await self._respond()

    async def _take_edge(self, node: Any) -> str | None:
        """Pick the outgoing edge that fires now, if any, and report it."""
        edges = self.out.get(node.id, [])
        for e in edges:
            if isinstance(e.condition, CelCondition) and cel_true(e.condition.expr, self.variables):
                return await self._fire(e)
        llm_edges = [e for e in edges if isinstance(e.condition, LlmCondition)]
        if llm_edges and any(m["role"] == "user" for m in self.history):
            chosen = await self._judge(llm_edges)
            if chosen:
                return await self._fire(chosen)
        for e in edges:
            if e.condition is None and (
                not isinstance(node, AgentStepNode) or self.replies_in_node > 0
            ):
                return await self._fire(e)
        for e in edges:
            if isinstance(e.condition, ElseCondition) and (
                not isinstance(node, AgentStepNode) or self.replies_in_node > 0
            ):
                return await self._fire(e)
        return None

    async def _fire(self, edge: Edge) -> str:
        condition = edge.condition.model_dump() if edge.condition else None
        await self.emit(
            "edge",
            {"edge_id": edge.id, "from": edge.source, "to": edge.target, "condition": condition},
        )
        return edge.target

    async def _judge(self, edges: list[Edge]) -> Edge | None:
        """One model call decides which (if any) of several natural-language conditions holds."""
        options = "\n".join(
            f"{i + 1}. {e.condition.text}"  # type: ignore[union-attr]
            for i, e in enumerate(edges)
        )
        messages = [
            {
                "role": "system",
                "content": "You route a phone conversation. Read the conversation and decide "
                "which numbered condition is true about the caller right now. Answer with the "
                "number of the first condition that clearly holds, or 0 if none does."
                "\n\nConditions:\n" + options,
            },
            {"role": "user", "content": self._transcript(last=8)},
        ]
        schema = {
            "type": "object",
            "properties": {"choice": {"type": "integer", "minimum": 0, "maximum": len(edges)}},
            "required": ["choice"],
        }
        self.usage["llm_calls"] += 1
        try:
            result = await self.llm.json(messages, model=self._model(), schema=schema)
            choice = int(result.get("choice", 0))
        except (ValueError, TypeError):
            return None
        return edges[choice - 1] if 1 <= choice <= len(edges) else None

    # speaking -----------------------------------------------------------------------------------

    async def _say(self, text: str, voice: VoiceSettings) -> None:
        self.history.append({"role": "assistant", "content": text})
        await self.emit(
            "assistant_message",
            {"text": text, "node_id": self.current, "voice": voice.model_dump(), "llm": None},
        )

    async def _respond(self) -> None:
        node = self.nodes[self.current]
        assert isinstance(node, AgentStepNode)
        voice = (
            node.data.overrides.voice if node.data.overrides else None
        ) or self.spec.settings.voice
        system = await self._system_prompt(node)
        tools = self._tools(node)
        messages: list[dict[str, Any]] = [{"role": "system", "content": system}, *self._history()]
        started = time.monotonic()
        first_token: float | None = None
        text = ""
        for _ in range(4):  # tool-call rounds
            calls: list[ToolCall] = []
            self.usage["llm_calls"] += 1
            async for chunk in self.llm.stream(
                messages, model=self._model(node), temperature=self._temperature(node), tools=tools
            ):
                if chunk.text:
                    if first_token is None:
                        first_token = time.monotonic()
                    text += chunk.text
                    await self.emit("token", {"text": chunk.text})
                if chunk.tool_call:
                    calls.append(chunk.tool_call)
            if not calls:
                break
            messages.append(
                {
                    "role": "assistant",
                    "content": text or None,
                    "tool_calls": [
                        {
                            "id": c.id,
                            "type": "function",
                            "function": {"name": c.name, "arguments": json.dumps(c.arguments)},
                        }
                        for c in calls
                    ],
                }
            )
            for call in calls:
                result = await self._run_tool(call, node)
                messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
            if self.ended:
                break
        total = time.monotonic() - started
        text = text.strip()
        if text:
            self.history.append({"role": "assistant", "content": text})
            self.replies_in_node += 1
            await self.emit(
                "assistant_message",
                {
                    "text": text,
                    "node_id": node.id,
                    "voice": voice.model_dump(),
                    "llm": {
                        "ttft_ms": round(((first_token or time.monotonic()) - started) * 1000),
                        "total_ms": round(total * 1000),
                    },
                },
            )
        if self.ended:
            await self.emit("ended", {"outcome": self.outcome})

    async def _system_prompt(self, node: AgentStepNode) -> str:
        parts = [render(self.spec.settings.prompt, self.variables)]
        if node.data.prompt:
            parts.append("Current step: " + render(node.data.prompt, self.variables))
        known = {k: v for k, v in self._flat_vars().items() if v is not None}
        if known:
            parts.append("Known details: " + json.dumps(known))
        if self.recalled:
            parts.append("What you remember about this caller:\n- " + "\n- ".join(self.recalled))
        if node.data.auto_knowledge_top_k and self.search_knowledge:
            last_user = next(
                (m["content"] for m in reversed(self.history) if m["role"] == "user"), ""
            )
            if last_user:
                hits = await self._knowledge(last_user, node, node.data.auto_knowledge_top_k)
                if hits:
                    parts.append("Reference material:\n" + "\n---\n".join(h["text"] for h in hits))
        if self.summary:
            parts.append("Earlier in this conversation: " + self.summary)
        parts.append("Reply in plain spoken sentences: no markdown, lists or emoji.")
        return "\n\n".join(p for p in parts if p)

    def _tools(self, node: AgentStepNode) -> list[dict[str, Any]] | None:
        names = {t.name for t in self.spec.tools if t.kind == "builtin"}
        if node.data.tools is not None:
            names &= {t.name for t in node.data.tools if t.kind == "builtin"}
        if not self.search_knowledge:
            names.discard("search_knowledge")
        if not (self.recall_memory and self.spec.memory.enabled):
            names.discard("recall_memory")
        else:
            names.add("recall_memory")
        tools = [
            {"type": "function", "function": {"name": n, **BUILTIN_TOOLS[n]}}
            for n in sorted(names)
            if n in BUILTIN_TOOLS
        ]
        return tools or None

    async def _run_tool(self, call: ToolCall, node: AgentStepNode) -> str:
        await self.emit("tool_call", {"name": call.name, "arguments": call.arguments})
        if call.name == "end_session":
            self.ended = True
            self.outcome = "ended_by_agent"
            result: Any = {"ok": True}
        elif call.name == "search_knowledge" and self.search_knowledge:
            result = await self._knowledge(str(call.arguments.get("query", "")), node, 4)
        elif call.name == "recall_memory" and self.recall_memory:
            result = await self.recall_memory(str(call.arguments.get("query", "")), 5)
            await self.emit("memory", {"recalled": [{"fact": f} for f in result]})
        else:
            result = {"error": f"Unknown tool {call.name}"}
        await self.emit("tool_result", {"name": call.name, "result": result})
        return json.dumps(result)

    async def _knowledge(self, query: str, node: AgentStepNode, k: int) -> list[dict[str, Any]]:
        assert self.search_knowledge
        sources = (
            [r.source_id for r in node.data.knowledge] if node.data.knowledge is not None else None
        )
        hits = await self.search_knowledge(query, sources, k)
        await self.emit("knowledge", {"query": query, "results": hits})
        return hits

    # extraction ---------------------------------------------------------------------------------

    async def _run_extract(self, node: ExtractNode, hops: int = 0) -> None:
        wanted = [self.declared[n] for n in node.data.outputs if n in self.declared]
        missing = [v for v in wanted if get_var(self.variables, v.name) is None]
        if missing and any(m["role"] == "user" for m in self.history):
            schema = {
                "type": "object",
                "properties": {v.name: _json_type(v) for v in missing},
                "required": [v.name for v in missing],
            }
            messages = [
                {
                    "role": "system",
                    "content": "Fill in each field from what the caller has said. Today is "
                    f"{date.today():%A %Y-%m-%d}; turn dates like 'next Tuesday' into YYYY-MM-DD. "
                    "Use an empty string for anything the caller has not mentioned.",
                },
                {"role": "user", "content": self._transcript(last=12)},
            ]
            self.usage["llm_calls"] += 1
            try:
                found = await self.llm.json(messages, model=self._model(), schema=schema)
            except (ValueError, TypeError):
                found = {}
            for var in missing:
                raw = found.get(var.name)
                if raw is None or raw == "":
                    continue
                if var.type == "object" and isinstance(raw, str):
                    with contextlib.suppress(json.JSONDecodeError):
                        raw = json.loads(raw)
                try:
                    await self._set_variable(var.name, coerce(var, raw))
                except ValueError as e:
                    await self.emit(
                        "variable_rejected", {"name": var.name, "value": raw, "reason": str(e)}
                    )
            missing = [v for v in wanted if get_var(self.variables, v.name) is None]
        if not missing:
            nxt = await self._take_edge(node)
            if nxt:
                await self._advance(nxt, hops + 1)
            return
        await self._ask_for(node, missing)

    async def _ask_for(self, node: ExtractNode, missing: list[VariableDef]) -> None:
        need = ", ".join(f"{v.name} ({v.description or v.type})" for v in missing)
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": render(self.spec.settings.prompt, self.variables)
                + f"\n\nYou still need: {need}. "
                + render(node.data.instructions, self.variables)
                + " Ask for the next missing detail in one short spoken sentence.",
            },
            *self._history(),
        ]
        started = time.monotonic()
        first: float | None = None
        text = ""
        self.usage["llm_calls"] += 1
        async for chunk in self.llm.stream(messages, model=self._model(), temperature=0.4):
            if chunk.text:
                first = first or time.monotonic()
                text += chunk.text
                await self.emit("token", {"text": chunk.text})
        text = text.strip()
        self.history.append({"role": "assistant", "content": text})
        await self.emit(
            "assistant_message",
            {
                "text": text,
                "node_id": node.id,
                "voice": self.spec.settings.voice.model_dump(),
                "llm": {
                    "ttft_ms": round(((first or time.monotonic()) - started) * 1000),
                    "total_ms": round((time.monotonic() - started) * 1000),
                },
            },
        )

    # state helpers ------------------------------------------------------------------------------

    async def _set_variable(self, name: str, value: Any) -> None:
        set_var(self.variables, name, value)
        await self.emit("variable_set", {"name": name, "value": value})

    def _cel_value(self, expr: str) -> Any:
        try:
            program = _cel_env.program(_cel_env.compile(expr))
            value = program.evaluate({k: json_to_cel(v) for k, v in self.variables.items()})  # type: ignore[arg-type]
            return json.loads(json.dumps(value, default=str))
        except Exception:
            return None

    def _flat_vars(self) -> dict[str, Any]:
        return {name: get_var(self.variables, name) for name in self.declared}

    def _model(self, node: AgentStepNode | None = None) -> str | None:
        if (
            node
            and node.data.overrides
            and node.data.overrides.llm
            and node.data.overrides.llm.model
        ):
            return node.data.overrides.llm.model
        return self.spec.settings.llm.model or self.default_model

    def _temperature(self, node: AgentStepNode) -> float:
        if node.data.overrides and node.data.overrides.llm:
            return node.data.overrides.llm.temperature
        return self.spec.settings.llm.temperature

    def _history(self) -> list[dict[str, Any]]:
        return [{"role": m["role"], "content": m["content"]} for m in self.history]

    def _transcript(self, last: int) -> str:
        who = {"user": "Caller", "assistant": "Agent"}
        return "\n".join(f"{who[m['role']]}: {m['content']}" for m in self.history[-last:])

    async def _compact_history(self) -> None:
        """Keep the conversation within the token budget by summarising the oldest half (FR-14)."""
        budget = self.spec.settings.history_token_budget
        total = sum(estimate_tokens(m["content"]) for m in self.history) + estimate_tokens(
            self.summary
        )
        if total <= budget or len(self.history) < 4:
            return
        cut = len(self.history) // 2
        old, self.history = self.history[:cut], self.history[cut:]
        text = "\n".join(f"{m['role']}: {m['content']}" for m in old)
        self.usage["llm_calls"] += 1
        try:
            result = await self.llm.json(
                [
                    {
                        "role": "system",
                        "content": "Summarise this earlier part of a phone call in under 80 words, "
                        "keeping names, numbers, dates and decisions.",
                    },
                    {"role": "user", "content": (self.summary + "\n" + text).strip()},
                ],
                model=self._model(),
                schema={
                    "type": "object",
                    "properties": {"summary": {"type": "string"}},
                    "required": ["summary"],
                },
            )
            self.summary = str(result.get("summary", ""))[:2000]
        except (ValueError, TypeError):
            self.summary = (self.summary + " " + text)[-2000:]
        await self.emit("summary", {"summary": self.summary, "dropped_messages": cut})
