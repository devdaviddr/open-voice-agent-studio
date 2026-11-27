"""A scripted OpenAI-compatible LLM for tests and the end-to-end suite. Never calls a real model.

Run it: `uv run uvicorn --app-dir services/runtime/tests stub_llm:app --port 8200`, then point
OVAS_DEFAULT_LLM_URL at http://<host>:8200/v1 (model name: anything).

Behaviour, deterministic:
- Chat replies echo the caller ("You said: …"). If the prompt holds remembered facts and the
  caller asks what the agent remembers, the reply lists them.
- Edge routing (`choice`): 1 when the caller says goodbye, else 0 (stay).
- Memory extraction (`facts`): "my dog is (called) X" and "my name is X" become facts.
- Summaries and Extract fields get fixed, empty-ish answers.
Streaming requests get Server-Sent Events in OpenAI's chunk format.
"""

import json
import re
import time
from collections.abc import Iterator
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI(title="stub LLM")

MODEL = "stub"
REMEMBERED = "What you remember about this caller:"


def _last(messages: list[dict[str, Any]], role: str) -> str:
    return next((str(m.get("content") or "") for m in reversed(messages) if m["role"] == role), "")


def _all_text(messages: list[dict[str, Any]]) -> str:
    return "\n".join(str(m.get("content") or "") for m in messages)


def facts_in(text: str) -> list[str]:
    facts = []
    if m := re.search(r"\bmy dog(?:'s| is)?(?: called| named)? ([A-Z][a-z]+)", text):
        facts.append(f"Their dog is called {m.group(1)}.")
    if m := re.search(r"\bmy name is ([A-Z][a-z]+)", text):
        facts.append(f"Their name is {m.group(1)}.")
    return facts


def chat_reply(messages: list[dict[str, Any]]) -> str:
    system, said = _last(messages, "system"), _last(messages, "user")
    if REMEMBERED in system and re.search(r"\bremember\b", said, re.I):
        lines = system.split(REMEMBERED, 1)[1].strip().split("\n\n", 1)[0]
        facts = [f.removeprefix("- ").strip() for f in lines.splitlines() if f.strip()]
        return "Yes, I remember: " + " ".join(facts)
    return f"You said: {said}" if said else "Hello, how can I help?"


def json_reply(messages: list[dict[str, Any]], schema: dict[str, Any]) -> dict[str, Any]:
    props = schema.get("properties", {})
    if "choice" in props:
        said = _last(messages, "user").lower()
        return {"choice": 1 if re.search(r"\b(bye|goodbye)\b", said) else 0}
    if "facts" in props:
        return {"facts": facts_in(_all_text(messages))}
    if "summary" in props:
        return {"summary": "The caller has been chatting."}
    return {name: "" for name in props}


def _schema(body: dict[str, Any]) -> dict[str, Any] | None:
    fmt = body.get("response_format") or {}
    if fmt.get("type") == "json_schema":
        return fmt["json_schema"]["schema"]
    if fmt.get("type") == "json_object":  # schema comes as a system hint
        hint = _last(body["messages"], "system")
        start = hint.find("{")
        return json.loads(hint[start:]) if start >= 0 else {}
    return None


def _sse(text: str) -> Iterator[str]:
    base = {
        "id": "stub",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": MODEL,
    }
    for i, word in enumerate(text.split(" ")):
        delta = {"content": ("" if i == 0 else " ") + word}
        yield "data: " + json.dumps({**base, "choices": [{"index": 0, "delta": delta}]}) + "\n\n"
    done = {"index": 0, "delta": {}, "finish_reason": "stop"}
    yield "data: " + json.dumps({**base, "choices": [done]}) + "\n\n"
    yield "data: [DONE]\n\n"


@app.get("/v1/models")
def models() -> dict:
    return {"object": "list", "data": [{"id": MODEL, "object": "model"}]}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/v1/chat/completions", response_model=None)
async def completions(request: Request) -> JSONResponse | StreamingResponse:
    body = await request.json()
    messages = body["messages"]
    schema = _schema(body)
    content = (
        json.dumps(json_reply(messages, schema)) if schema is not None else chat_reply(messages)
    )
    if body.get("stream"):
        return StreamingResponse(_sse(content), media_type="text/event-stream")
    return JSONResponse(
        {
            "id": "stub",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": MODEL,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
    )
