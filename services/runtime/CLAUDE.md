# services/runtime — sessions

Runs agent sessions. The MVP serves text sessions over WebSocket; Pipecat voice arrives in M2
(ADR-0004). The workflow logic itself lives in `ovas_core.engine` so it is testable without the
runtime; this service only handles transport, auth tokens and event persistence.
