"""The AgentSpec schema: the single source of truth for an agent's workflow and settings.

Mirrors spec/product §7. TypeScript types for the studio are generated from this module
(`make gen`), so change it here and regenerate; never edit the generated files.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1"

VAR_NAME = r"^[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)*$"


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", json_schema_serialization_defaults_required=True)


# --- settings -------------------------------------------------------------------------------


class VoiceSettings(Model):
    provider: str = "kokoro"
    voice_id: str = "af_heart"
    speed: float = Field(default=1.0, ge=0.5, le=2.0)


class LlmSettings(Model):
    provider: str = "workspace"
    model: str | None = None
    temperature: float = Field(default=0.6, ge=0.0, le=2.0)


class SttSettings(Model):
    provider: str = "whisper"
    model: str = "small.en"


class TurnSettings(Model):
    sensitivity: Literal["low", "medium", "high"] = "medium"
    interruptions: bool = True


class Limits(Model):
    max_session_seconds: int = Field(default=900, ge=10)
    idle_timeout_seconds: int = Field(default=30, ge=5)


class AgentSettings(Model):
    prompt: str = ""
    first_message: str = ""
    language: str = "en"
    voice: VoiceSettings = Field(default_factory=VoiceSettings)
    llm: LlmSettings = Field(default_factory=LlmSettings)
    stt: SttSettings = Field(default_factory=SttSettings)
    turn: TurnSettings = Field(default_factory=TurnSettings)
    limits: Limits = Field(default_factory=Limits)
    history_token_budget: int = Field(default=4000, ge=500)


class SettingsOverride(Model):
    """Per-node overrides; unset fields inherit the agent's settings."""

    language: str | None = None
    voice: VoiceSettings | None = None
    llm: LlmSettings | None = None


# --- references -----------------------------------------------------------------------------

BuiltinTool = Literal[
    "end_session", "go_to_node", "set_variable", "search_knowledge", "recall_memory"
]


class BuiltinToolRef(Model):
    kind: Literal["builtin"] = "builtin"
    name: BuiltinTool


class WorkspaceToolRef(Model):
    kind: Literal["workspace"] = "workspace"
    tool_id: str


ToolRef = Annotated[BuiltinToolRef | WorkspaceToolRef, Field(discriminator="kind")]


class KnowledgeRef(Model):
    source_id: str


class VariableDef(Model):
    name: str = Field(pattern=VAR_NAME)
    type: Literal["string", "number", "boolean", "date", "email", "enum", "object"] = "string"
    enum: list[str] | None = None
    description: str = ""


class PronunciationEntry(Model):
    term: str = Field(min_length=1)
    say: str = Field(min_length=1)


# --- graph ----------------------------------------------------------------------------------


class Position(Model):
    x: float
    y: float


class StartData(Model):
    first_message: str | None = None
    set: dict[str, str] = Field(default_factory=dict, description="Variable name → CEL expression")


class AgentStepData(Model):
    label: str
    prompt: str = ""
    overrides: SettingsOverride | None = None
    tools: list[ToolRef] | None = Field(
        default=None, description="Narrow the agent's tools; null = all"
    )
    knowledge: list[KnowledgeRef] | None = Field(
        default=None, description="Narrow knowledge; null = all"
    )
    auto_knowledge_top_k: int = Field(default=0, ge=0, le=10)


class ExtractData(Model):
    label: str
    instructions: str = ""
    outputs: list[str] = Field(
        default_factory=list, description="Names of declared variables to fill"
    )


class RouterData(Model):
    label: str


class ToolCallData(Model):
    label: str
    tool: ToolRef
    args: dict[str, str] = Field(default_factory=dict, description="Argument → CEL expression")
    result_map: dict[str, str] = Field(default_factory=dict, description="Variable → JSONPath")


class HandoffData(Model):
    label: str
    agent_id: str
    environment: str = "live"
    pass_variables: list[str] = Field(default_factory=list)


class EndData(Model):
    label: str = "End"
    message: str | None = None
    outcome: str = "completed"


class NoteData(Model):
    text: str


class _Node(Model):
    id: str = Field(min_length=1)
    position: Position


class StartNode(_Node):
    type: Literal["start"] = "start"
    data: StartData = Field(default_factory=StartData)


class AgentStepNode(_Node):
    type: Literal["agent_step"] = "agent_step"
    data: AgentStepData


class ExtractNode(_Node):
    type: Literal["extract"] = "extract"
    data: ExtractData


class RouterNode(_Node):
    type: Literal["router"] = "router"
    data: RouterData


class ToolCallNode(_Node):
    type: Literal["tool_call"] = "tool_call"
    data: ToolCallData


class HandoffNode(_Node):
    type: Literal["handoff"] = "handoff"
    data: HandoffData


class EndNode(_Node):
    type: Literal["end"] = "end"
    data: EndData = Field(default_factory=EndData)


class NoteNode(_Node):
    type: Literal["note"] = "note"
    data: NoteData


Node = Annotated[
    StartNode
    | AgentStepNode
    | ExtractNode
    | RouterNode
    | ToolCallNode
    | HandoffNode
    | EndNode
    | NoteNode,
    Field(discriminator="type"),
]

NodeType = Literal[
    "start", "agent_step", "extract", "router", "tool_call", "handoff", "end", "note"
]


class LlmCondition(Model):
    kind: Literal["llm"] = "llm"
    text: str = Field(min_length=1)


class CelCondition(Model):
    kind: Literal["cel"] = "cel"
    expr: str = Field(min_length=1)


class ElseCondition(Model):
    kind: Literal["else"] = "else"


Condition = Annotated[LlmCondition | CelCondition | ElseCondition, Field(discriminator="kind")]


class Edge(Model):
    id: str = Field(min_length=1)
    source: str
    target: str
    order: int = 0
    condition: Condition | None = Field(default=None, description="null = always (unconditional)")


class Graph(Model):
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)


class MemorySettings(Model):
    enabled: bool = False


class RecordingSettings(Model):
    enabled: bool = False


class AgentSpec(Model):
    schema_version: Literal["1"] = SCHEMA_VERSION
    settings: AgentSettings = Field(default_factory=AgentSettings)
    graph: Graph = Field(default_factory=Graph)
    tools: list[ToolRef] = Field(default_factory=list)
    knowledge: list[KnowledgeRef] = Field(default_factory=list)
    variables: list[VariableDef] = Field(default_factory=list)
    pronunciation: list[PronunciationEntry] = Field(default_factory=list)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    recording: RecordingSettings = Field(default_factory=RecordingSettings)


def blank_spec() -> AgentSpec:
    """A new agent: Start → one Agent step → End."""
    return AgentSpec(
        settings=AgentSettings(
            prompt="You are a helpful voice assistant. Keep replies short and conversational.",
            first_message="Hi! How can I help you today?",
        ),
        graph=Graph(
            nodes=[
                StartNode(id="start", position=Position(x=0, y=0)),
                AgentStepNode(
                    id="main",
                    position=Position(x=300, y=-20),
                    data=AgentStepData(label="Conversation"),
                ),
                EndNode(id="end", position=Position(x=640, y=0)),
            ],
            edges=[
                Edge(id="e-start-main", source="start", target="main"),
                Edge(
                    id="e-main-end",
                    source="main",
                    target="end",
                    condition=LlmCondition(text="the caller has what they need or says goodbye"),
                ),
            ],
        ),
    )
