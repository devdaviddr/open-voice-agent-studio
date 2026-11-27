"""OpenAI-compatible LLM adapter for the engine (Ollama, vLLM, llama.cpp, Strata, OpenAI, ...)."""

import json
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI, BadRequestError

from ovas_core.engine import LlmChunk, ToolCall


class OpenAICompatibleLlm:
    def __init__(
        self,
        base_url: str,
        default_model: str,
        api_key: str | None = None,
        reasoning_effort: str | None = None,
    ) -> None:
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key or "not-needed", max_retries=1)
        self.default_model = default_model
        self.extra = {"reasoning_effort": reasoning_effort} if reasoning_effort else {}

    async def stream(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None,
        temperature: float,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[LlmChunk]:
        kwargs: dict[str, Any] = {"tools": tools} if tools else {}
        stream = await self.client.chat.completions.create(
            model=model or self.default_model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            stream=True,
            extra_body=self.extra,
            **kwargs,
        )
        pending: dict[int, dict[str, str]] = {}
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                yield LlmChunk(text=delta.content)
            for call in delta.tool_calls or []:
                slot = pending.setdefault(call.index, {"id": "", "name": "", "args": ""})
                slot["id"] = call.id or slot["id"]
                if call.function:
                    slot["name"] = call.function.name or slot["name"]
                    slot["args"] += call.function.arguments or ""
        for i, slot in sorted(pending.items()):
            try:
                args = json.loads(slot["args"] or "{}")
            except json.JSONDecodeError:
                args = {}
            yield LlmChunk(
                tool_call=ToolCall(id=slot["id"] or f"call_{i}", name=slot["name"], arguments=args)
            )

    async def json(
        self, messages: list[dict[str, Any]], *, model: str | None, schema: dict[str, Any]
    ) -> dict[str, Any]:
        """Structured output via json_schema; falls back to json_object for older servers."""
        try:
            res = await self.client.chat.completions.create(
                model=model or self.default_model,
                messages=messages,  # type: ignore[arg-type]
                temperature=0,
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": "result", "schema": schema},
                },  # type: ignore[arg-type]
                extra_body=self.extra,
            )
        except BadRequestError:
            hint = {"role": "system", "content": "Reply with JSON matching: " + json.dumps(schema)}
            res = await self.client.chat.completions.create(
                model=model or self.default_model,
                messages=[*messages, hint],  # type: ignore[arg-type]
                temperature=0,
                response_format={"type": "json_object"},
                extra_body=self.extra,
            )
        text = res.choices[0].message.content or "{}"
        start, end = text.find("{"), text.rfind("}")
        result = json.loads(text[start : end + 1] if start >= 0 else "{}")
        if not isinstance(result, dict):
            raise ValueError("model did not return an object")
        return result
