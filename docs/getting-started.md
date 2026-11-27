# Getting started

This takes you from a clean machine to talking with your first agent, in about ten minutes.

## 1. Requirements

- Docker with Compose v2 (Docker Desktop, Colima or plain Docker Engine).
- An OpenAI-compatible LLM. The default is [Ollama](https://ollama.com) on the same machine with
  `qwen3.5:9b` pulled (`ollama pull qwen3.5:9b`). Anything else that speaks `/v1/chat/completions`
  works too: llama.cpp, vLLM, LM Studio or a hosted API. You can change it later in Settings.
- About 2 GB of free disk for images and models.

For development you also need [uv](https://docs.astral.sh/uv/) and [pnpm](https://pnpm.io) 11 with
Node 22.

## 2. Start the stack

```sh
git clone https://github.com/devdaviddr/open-voice-agent-studio.git
cd open-voice-agent-studio
make up
```

Open http://localhost:5173.

Models download once, on first use, into Docker volumes:

| Model | Used for | Size | When |
| --- | --- | --- | --- |
| Kokoro-82M | Reading replies aloud | about 350 MB | first start |
| Whisper `base` | Push-to-talk | about 145 MB | first recording |
| bge-small-en-v1.5 | Knowledge and memory search | about 130 MB | first document or memory |

For anything other than a laptop, copy `.env.example` to `.env` and set `OVAS_SECRET_KEY` and
`OVAS_INTERNAL_KEY` (`openssl rand -hex 32` each).

## 3. Create an account

Sign up. The first account owns the workspace. Anyone else who signs up joins it as a member while
**open sign-up** is on (Settings). There is no password reset by email yet.

## 4. Connect your LLM

Open **Settings → LLM**. With Ollama on the same machine the defaults already work. Otherwise enter
the base URL (ending in `/v1`), the model name and, if it needs one, an API key. Press **Test
connection**: it lists the models the endpoint offers. The key is stored encrypted and never shown
again.

## 5. Build an agent

1. **Agents → New agent**, pick **Dental receptionist** (a complete example) or **Blank**.
2. Click a node to edit it in the inspector on the right. Drag from a node's right handle to
   another node to connect them; click an edge to set its condition.
3. Problems (an unreachable step, a Router without `else`, an unknown variable) show on the canvas.
   The draft saves itself.

See [Concepts](concepts.md) for nodes, edges, variables and versions.

## 6. Test it

Press **Test**. Choose the draft or a version, optionally a **test caller ID** (needed for memory),
and **Start session**. Type, or press the mic to talk. The canvas shows which step is active and
what it is doing; the console lists every decision. Turn on the speaker icon to hear replies.

Every session is kept under **Sessions** with its transcript and events.

## 7. Give it knowledge and memory

- **Knowledge**: upload Markdown, text or PDF files, then tick them under **Knowledge** in the
  agent's settings. The agent can search them, and an Agent step can add the best passages to
  every turn.
- **Memory**: switch on **Long-term memory**, set a test caller ID, chat, end the session. A new
  session for the same caller starts with what it learned. **Memories** shows and deletes it.

## 8. Publish

**Publish** freezes the draft as version 1 and makes it live. Keep editing the draft; **Versions**
compares any two and can restore or roll back.

## Troubleshooting

- **"The agent could not reply: APIConnectionError"**: the LLM endpoint is not reachable from the
  containers. From Docker, the host is `host.docker.internal`, not `localhost`. Check Settings →
  LLM → Test connection.
- **Port already in use**: another app holds 5173, 8000, 8100, 8002 or 8003. Stop it, or override
  the ports in a Compose override file.
- **Sign-in is refused from another URL**: add that origin to `OVAS_ALLOWED_ORIGINS`.
- **Services** in the sidebar shows which backend services are up.
