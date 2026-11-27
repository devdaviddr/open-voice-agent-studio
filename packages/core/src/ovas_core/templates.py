"""Starter agents. "receptionist" exercises every MVP node type and all three edge conditions."""

from ovas_core.spec import (
    AgentSettings,
    AgentSpec,
    AgentStepData,
    AgentStepNode,
    BuiltinToolRef,
    CelCondition,
    Edge,
    ElseCondition,
    EndData,
    EndNode,
    ExtractData,
    ExtractNode,
    Graph,
    LlmCondition,
    NoteData,
    NoteNode,
    Position,
    RouterData,
    RouterNode,
    StartData,
    StartNode,
    VariableDef,
    blank_spec,
)


def receptionist() -> AgentSpec:
    def at(x: float, y: float) -> Position:
        return Position(x=x, y=y)

    return AgentSpec(
        settings=AgentSettings(
            prompt=(
                "You are Ava, the receptionist at Bright Smile Dental. You are friendly, calm and "
                "brief: one or two short sentences per reply. Never invent prices or opening "
                "hours; look them up."
            ),
            first_message="Hi, Bright Smile Dental, this is Ava. How can I help you today?",
        ),
        variables=[
            VariableDef(name="caller.name", type="string", description="The caller's full name"),
            VariableDef(
                name="caller.phone", type="string", description="A phone number to reach them"
            ),
            VariableDef(
                name="preferred_date", type="date", description="The day they want to come in"
            ),
            VariableDef(
                name="appointment_type",
                type="enum",
                enum=["cleaning", "checkup", "emergency"],
                description="What the visit is for",
            ),
        ],
        tools=[BuiltinToolRef(name="end_session"), BuiltinToolRef(name="search_knowledge")],
        graph=Graph(
            nodes=[
                StartNode(id="start", position=at(0, 200), data=StartData()),
                AgentStepNode(
                    id="triage",
                    position=at(280, 180),
                    data=AgentStepData(
                        label="Triage",
                        prompt="Find out whether the caller wants to book a visit, has a question "
                        "about the clinic, or is done.",
                    ),
                ),
                ExtractNode(
                    id="collect",
                    position=at(620, 20),
                    data=ExtractData(
                        label="Collect details",
                        instructions="Ask for anything missing, one item at a time.",
                        outputs=[
                            "caller.name",
                            "caller.phone",
                            "preferred_date",
                            "appointment_type",
                        ],
                    ),
                ),
                RouterNode(id="route", position=at(940, 40), data=RouterData(label="Emergency?")),
                AgentStepNode(
                    id="emergency",
                    position=at(1240, -80),
                    data=AgentStepData(
                        label="Emergency advice",
                        prompt="Tell {{caller.name}} we will fit them in today and that the clinic "
                        "will call {{caller.phone}} within 15 minutes. If they are in severe "
                        "pain or bleeding heavily, tell them to call 000.",
                    ),
                ),
                AgentStepNode(
                    id="confirm",
                    position=at(1240, 120),
                    data=AgentStepData(
                        label="Confirm booking",
                        prompt="Read the booking back to {{caller.name}}: a "
                        "{{appointment_type}} on {{preferred_date}}. Ask them to confirm.",
                    ),
                ),
                EndNode(
                    id="booked",
                    position=at(1560, 40),
                    data=EndData(label="Booked", outcome="booked"),
                ),
                AgentStepNode(
                    id="faq",
                    position=at(620, 300),
                    data=AgentStepData(
                        label="Clinic FAQ",
                        prompt="Answer questions about hours, prices and location using the "
                        "knowledge base only.",
                        auto_knowledge_top_k=3,
                    ),
                ),
                EndNode(
                    id="answered",
                    position=at(940, 320),
                    data=EndData(
                        label="Answered", message="Glad I could help. Bye!", outcome="faq"
                    ),
                ),
                EndNode(
                    id="goodbye",
                    position=at(620, 480),
                    data=EndData(
                        label="Goodbye", message="Thanks for calling. Bye!", outcome="ended"
                    ),
                ),
                NoteNode(
                    id="note",
                    position=at(260, 420),
                    data=NoteData(
                        text="Prices and hours must come from the knowledge base, never from the "
                        "model. Upload the clinic handbook in Knowledge."
                    ),
                ),
            ],
            edges=[
                Edge(id="e-start", source="start", target="triage"),
                Edge(
                    id="e-book",
                    source="triage",
                    target="collect",
                    order=1,
                    condition=LlmCondition(text="wants to book or move an appointment"),
                ),
                Edge(
                    id="e-faq",
                    source="triage",
                    target="faq",
                    order=2,
                    condition=LlmCondition(text="asks about hours, prices or location"),
                ),
                Edge(
                    id="e-bye",
                    source="triage",
                    target="goodbye",
                    order=3,
                    condition=LlmCondition(text="has nothing else and wants to end the call"),
                ),
                Edge(id="e-collected", source="collect", target="route"),
                Edge(
                    id="e-emergency",
                    source="route",
                    target="emergency",
                    order=1,
                    condition=CelCondition(expr='appointment_type == "emergency"'),
                ),
                Edge(
                    id="e-routine",
                    source="route",
                    target="confirm",
                    order=2,
                    condition=ElseCondition(),
                ),
                Edge(
                    id="e-confirmed",
                    source="confirm",
                    target="booked",
                    order=1,
                    condition=LlmCondition(text="confirmed the booking"),
                ),
                Edge(
                    id="e-emergency-done",
                    source="emergency",
                    target="booked",
                    order=1,
                    condition=LlmCondition(text="understood the next steps"),
                ),
                Edge(
                    id="e-answered",
                    source="faq",
                    target="answered",
                    order=1,
                    condition=LlmCondition(text="has no more questions"),
                ),
            ],
        ),
    )


TEMPLATES = {"blank": blank_spec, "receptionist": receptionist}
