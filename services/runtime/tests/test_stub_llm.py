"""The stub LLM drives the real OpenAI-compatible adapter (as the end-to-end suite does)."""

import httpx
import pytest
from openai import AsyncOpenAI

from ovas_runtime.llm import OpenAICompatibleLlm

from . import stub_llm


@pytest.fixture
def llm():
    llm = OpenAICompatibleLlm(base_url="http://stub/v1", default_model="stub")
    http = httpx.AsyncClient(transport=httpx.ASGITransport(app=stub_llm.app))
    llm.client = AsyncOpenAI(base_url="http://stub/v1", api_key="x", http_client=http)
    return llm


async def test_streams_an_echo(llm):
    chunks = [
        c.text
        async for c in llm.stream(
            [{"role": "user", "content": "Hi there"}], model=None, temperature=0
        )
    ]
    assert "".join(t or "" for t in chunks) == "You said: Hi there"


async def test_routes_on_goodbye(llm):
    schema = {"type": "object", "properties": {"choice": {"type": "integer"}}}
    bye = await llm.json([{"role": "user", "content": "ok bye"}], model=None, schema=schema)
    stay = await llm.json([{"role": "user", "content": "tell me more"}], model=None, schema=schema)
    assert bye == {"choice": 1} and stay == {"choice": 0}


async def test_extracts_memory_and_recalls_it(llm):
    schema = {"type": "object", "properties": {"facts": {"type": "array"}}}
    found = await llm.json(
        [{"role": "user", "content": "Caller: my dog is called Rex"}], model=None, schema=schema
    )
    assert found == {"facts": ["Their dog is called Rex."]}
    system = (
        "Be kind.\n\nWhat you remember about this caller:\n- Their dog is called Rex.\n\nReply."
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": "Do you remember me?"},
    ]
    reply = "".join([c.text or "" async for c in llm.stream(messages, model=None, temperature=0)])
    assert reply == "Yes, I remember: Their dog is called Rex."
