"""Ask the workspace LLM for durable facts in a finished conversation."""

import json
from typing import Any

import httpx

from ovas_api.routes.llm import ResolvedLlm

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"facts": {"type": "array", "items": {"type": "string"}, "maxItems": 10}},
    "required": ["facts"],
    "additionalProperties": False,
}

PROMPT = """You maintain long-term memory about one caller for a voice agent.
Read the conversation and list durable facts about the caller that would help in a future
conversation: names (theirs, family, pets), preferences, needs, bookings and commitments.
Write each as a short third-person sentence, for example "Their dog is called Rex."
Leave out greetings, small talk, anything only true for this call, and anything already known.
If there is nothing worth remembering, return an empty list.

Already known:
{known}

Conversation:
{transcript}"""

# Tests swap this for an httpx.MockTransport that answers like an OpenAI-compatible server.
transport: httpx.AsyncBaseTransport | None = None


def _parse(text: str) -> list[str]:
    start, end = text.find("{"), text.rfind("}")
    try:
        data = json.loads(text[start : end + 1]) if start >= 0 else {}
    except json.JSONDecodeError:
        return []
    facts = data.get("facts", []) if isinstance(data, dict) else []
    return [f.strip() for f in facts if isinstance(f, str) and f.strip()][:10]


async def extract_facts(llm: ResolvedLlm, transcript: str, known: list[str]) -> list[str]:
    prompt = PROMPT.format(
        known="\n".join(f"- {k}" for k in known) or "(nothing)", transcript=transcript
    )
    body: dict[str, Any] = {
        "model": llm.model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "memory", "schema": SCHEMA},
        },
    }
    if llm.reasoning_effort:
        body["reasoning_effort"] = llm.reasoning_effort
    headers = {"authorization": f"Bearer {llm.api_key}"} if llm.api_key else {}
    async with httpx.AsyncClient(timeout=120.0, transport=transport) as client:
        res = await client.post(f"{llm.base_url}/chat/completions", json=body, headers=headers)
        if res.status_code == 400:  # older servers: plain JSON mode with the schema as a hint
            body["response_format"] = {"type": "json_object"}
            body["messages"].append(
                {"role": "system", "content": "Reply with JSON matching: " + json.dumps(SCHEMA)}
            )
            res = await client.post(f"{llm.base_url}/chat/completions", json=body, headers=headers)
        res.raise_for_status()
        content = res.json()["choices"][0]["message"].get("content") or "{}"
    return _parse(content)
