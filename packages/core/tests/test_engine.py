import pytest

from ovas_core.engine import TextSession, ToolCall, coerce, render
from ovas_core.spec import (
    AgentStepData,
    AgentStepNode,
    BuiltinToolRef,
    LlmSettings,
    Position,
    SettingsOverride,
    VariableDef,
    blank_spec,
)
from ovas_core.templates import receptionist
from ovas_core.testing import FakeLlm


class Recorder:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    async def __call__(self, kind: str, payload: dict) -> None:
        self.events.append((kind, payload))

    def kinds(self) -> list[str]:
        return [k for k, _ in self.events]

    def of(self, kind: str) -> list[dict]:
        return [p for k, p in self.events if k == kind]

    def says(self) -> list[str]:
        return [p["text"] for p in self.of("assistant_message")]


async def run(spec, llm, variables=None):
    rec = Recorder()
    session = TextSession(
        spec=spec, llm=llm, emit=rec, default_model="test-model", variables=variables or {}
    )
    await session.start()
    return session, rec


async def test_first_message_renders_seeded_variables():  # MVP AC-12
    spec = blank_spec()
    spec.variables = [VariableDef(name="caller.name")]
    spec.settings.first_message = "Hi {{caller.name}}, how can I help?"
    _, rec = await run(spec, FakeLlm(), variables={"caller": {"name": "Ana"}})
    assert rec.says() == ["Hi Ana, how can I help?"]
    assert rec.of("node_enter")[-1] == {"node_id": "main"}


async def test_receptionist_books_an_emergency():
    def extract(props):
        values = {
            "caller.name": "Ana Lopez",
            "caller.phone": "0412 555 019",
            "preferred_date": "2026-12-01",
            "appointment_type": "emergency",
        }
        return {k: values.get(k) for k in props}

    llm = FakeLlm(replies=["We will see you today, Ana."], choices=[1], extract=extract)
    session, rec = await run(receptionist(), llm)
    await session.user_message(
        "My tooth is killing me, I need to come in today. Ana Lopez, 0412 555 019."
    )
    path = [p["node_id"] for p in rec.of("node_enter")]
    assert path == ["start", "triage", "collect", "route", "emergency"]
    assert session.variables["appointment_type"] == "emergency"
    assert session.variables["caller"] == {"name": "Ana Lopez", "phone": "0412 555 019"}
    assert rec.says()[-1] == "We will see you today, Ana."
    # The router's CEL edge fired without asking the model (product AC-6).
    judge_calls = [c for c in llm.json_calls if "choice" in c["schema"]["properties"]]
    assert len(judge_calls) == 1  # only Triage's model-judged edges


async def test_extract_rejects_invalid_values_and_asks_again():  # MVP AC-12
    def extract(props):
        return {
            k: {"preferred_date": "next Tuesday-ish", "caller.name": "Ana"}.get(k) for k in props
        }

    llm = FakeLlm(replies=["What day suits you?"], choices=[1], extract=extract)
    session, rec = await run(receptionist(), llm)
    await session.user_message("I'd like a cleaning. I'm Ana.")
    assert session.current == "collect"
    rejected = rec.of("variable_rejected")
    assert [r["name"] for r in rejected] == ["preferred_date"]
    assert session.variables == {"caller": {"name": "Ana"}}
    assert rec.says()[-1] == "What day suits you?"


async def test_no_edge_fires_so_current_step_replies():
    llm = FakeLlm(replies=["Sure, what would you like to know?"], choices=[0])
    session, rec = await run(receptionist(), llm)
    await session.user_message("Hmm, hello?")
    assert session.current == "triage"
    assert rec.says()[-1] == "Sure, what would you like to know?"


async def test_end_node_says_goodbye_and_ends():
    llm = FakeLlm(choices=[3])
    session, rec = await run(receptionist(), llm)
    await session.user_message("No thanks, that's all.")
    assert session.ended and session.outcome == "ended"
    assert rec.says()[-1] == "Thanks for calling. Bye!"
    assert rec.kinds()[-1] == "ended"


async def test_node_model_override_is_used():  # MVP AC-8
    spec = blank_spec()
    main = spec.graph.nodes[1]
    assert isinstance(main, AgentStepNode)
    main.data.overrides = SettingsOverride(llm=LlmSettings(model="big-model", temperature=0.1))
    llm = FakeLlm(replies=["Hello!"], choices=[0])
    session, _ = await run(spec, llm)
    await session.user_message("Hi")
    assert llm.stream_calls[-1]["model"] == "big-model"


async def test_history_stays_within_budget():  # MVP AC-13
    spec = blank_spec()
    spec.settings.history_token_budget = 500
    llm = FakeLlm(replies=["A fairly long answer " * 10] * 60, choices=[0] * 60)
    session, rec = await run(spec, llm)
    for i in range(60):
        await session.user_message(f"Question number {i}: " + "tell me more about that " * 8)
    sent = [
        sum(len(m["content"] or "") // 4 for m in call["messages"] if m["role"] != "system")
        for call in llm.stream_calls
    ]
    assert max(sent) <= 500 + 150  # budget plus the newest exchange
    assert rec.of("summary")


async def test_end_session_tool_ends_the_conversation():
    spec = blank_spec()
    spec.tools = [BuiltinToolRef(name="end_session")]
    llm = FakeLlm(
        replies=[ToolCall(id="1", name="end_session", arguments={}), "Goodbye!"], choices=[0]
    )
    session, rec = await run(spec, llm)
    await session.user_message("Bye")
    assert session.ended
    assert rec.of("tool_call")[0]["name"] == "end_session"
    assert llm.stream_calls[0]["tools"][0]["function"]["name"] == "end_session"


async def test_search_knowledge_tool_answers_from_documents():  # MVP AC-14
    spec = blank_spec()
    spec.tools = [BuiltinToolRef(name="search_knowledge")]
    llm = FakeLlm(
        replies=[
            ToolCall(id="1", name="search_knowledge", arguments={"query": "cleaning price"}),
            "A cleaning costs 145 dollars.",
        ],
        choices=[0],
    )
    searches: list[tuple[str, list[str] | None, int]] = []

    async def search(query, sources, k):
        searches.append((query, sources, k))
        return [{"source": "handbook.md", "text": "A standard cleaning costs 145 dollars."}]

    rec = Recorder()
    session = TextSession(spec=spec, llm=llm, emit=rec, search_knowledge=search)
    await session.start()
    await session.user_message("How much is a cleaning?")
    assert searches == [("cleaning price", None, 4)]
    assert rec.of("knowledge")[0]["results"][0]["source"] == "handbook.md"
    assert rec.of("assistant_message")[-1]["text"] == "A cleaning costs 145 dollars."
    tool_reply = next(m for m in llm.stream_calls[-1]["messages"] if m["role"] == "tool")
    assert "145 dollars" in tool_reply["content"]


async def test_search_tool_hidden_without_a_search_function():
    spec = blank_spec()
    spec.tools = [BuiltinToolRef(name="search_knowledge")]
    llm = FakeLlm(replies=["Hi.", "OK."], choices=[0])
    session, _ = await run(spec, llm)
    await session.user_message("Hello")
    assert llm.stream_calls[-1]["tools"] is None


async def test_memory_recalled_at_start_and_by_tool():  # MVP AC-15
    spec = blank_spec()
    spec.memory.enabled = True
    llm = FakeLlm(
        replies=[
            ToolCall(id="1", name="recall_memory", arguments={"query": "pet"}),
            "Of course, how is Rex?",
        ],
        choices=[0],
    )
    asked: list[tuple[str, int]] = []

    async def recall(query, k):
        asked.append((query, k))
        return ["Their dog is called Rex."]

    rec = Recorder()
    session = TextSession(spec=spec, llm=llm, emit=rec, recall_memory=recall)
    await session.start()
    assert asked == [("", 5)] and session.recalled == ["Their dog is called Rex."]
    await session.user_message("Do you remember my pet?")
    assert asked[1] == ("pet", 5)
    assert [m["recalled"][0]["fact"] for m in rec.of("memory")] == ["Their dog is called Rex."] * 2
    system = llm.stream_calls[0]["messages"][0]["content"]
    assert "What you remember about this caller:\n- Their dog is called Rex." in system
    tools = [t["function"]["name"] for t in llm.stream_calls[0]["tools"]]
    assert "recall_memory" in tools


async def test_memory_off_never_recalls():
    spec = blank_spec()
    called = []

    async def recall(query, k):
        called.append(query)
        return ["x"]

    session = TextSession(
        spec=spec, llm=FakeLlm(replies=["Hi."]), emit=Recorder(), recall_memory=recall
    )
    await session.start()
    await session.user_message("Hello")
    assert called == []


def test_render_and_coerce():
    assert render("Hi {{a.b}} {{missing}}!", {"a": {"b": "Ana"}}) == "Hi Ana !"
    assert coerce(VariableDef(name="d", type="date"), "2026-12-01") == "2026-12-01"
    assert coerce(VariableDef(name="n", type="number"), "4") == 4
    assert coerce(VariableDef(name="e", type="enum", enum=["a"]), "a") == "a"
    for var, bad in [
        (VariableDef(name="d", type="date"), "tuesday"),
        (VariableDef(name="m", type="email"), "nope"),
        (VariableDef(name="e", type="enum", enum=["a"]), "b"),
    ]:
        with pytest.raises(ValueError):
            coerce(var, bad)


async def test_step_without_prompt_still_runs():
    spec = blank_spec()
    spec.graph.nodes.append(
        AgentStepNode(id="x", position=Position(x=0, y=0), data=AgentStepData(label="X"))
    )
    session, _ = await run(spec, FakeLlm(replies=["Hi"], choices=[0]))
    await session.user_message("hello")
    assert session.current == "main"
