"""Test helpers: a scripted stand-in for the LLM, used by engine and runtime tests."""

from collections.abc import AsyncIterator, Callable, Sequence
from typing import Any

from ovas_core.engine import LlmChunk, ToolCall


class FakeLlm:
    def __init__(
        self,
        replies: Sequence[str | ToolCall] | None = None,
        choices: list[int] | None = None,
        extract: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> None:
        self.replies = list(replies or [])
        self.choices = list(choices or [])
        self.extract = extract or (lambda props: {k: None for k in props})
        self.stream_calls: list[dict[str, Any]] = []
        self.json_calls: list[dict[str, Any]] = []

    async def stream(self, messages, *, model, temperature, tools=None) -> AsyncIterator[LlmChunk]:
        self.stream_calls.append({"messages": messages, "model": model, "tools": tools})
        reply = self.replies.pop(0) if self.replies else "OK."
        if isinstance(reply, ToolCall):
            yield LlmChunk(tool_call=reply)
            return
        for word in reply.split(" "):
            yield LlmChunk(text=word + " ")

    async def json(self, messages, *, model, schema) -> dict[str, Any]:
        self.json_calls.append({"messages": messages, "model": model, "schema": schema})
        props = schema["properties"]
        if "choice" in props:
            return {"choice": self.choices.pop(0) if self.choices else 0}
        if "summary" in props:
            return {"summary": "Caller is chatting."}
        return self.extract(props)
