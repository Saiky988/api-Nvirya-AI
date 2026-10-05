# Nvirya AI

**Nvirya AI** is a production-oriented AI API Gateway and server-side Agent Runtime. It exposes a standard OpenAI-compatible API while embedding a full orchestration layer capable of model routing, multi-step tool execution, web search, web page extraction, task quotas, rate limiting, and persistent artifact generation.

The initial upstream AI provider is **xKiro** (`https://api.xkiro.com/v1`).

---

## Key Features

* **OpenAI-Compatible Endpoints**: Seamless drop-in replacement for `/v1/chat/completions` and `/v1/models`.
* **Server-Side Agent Runtime**: The backend executes requested tools (calculator, web search, web fetch, file creation) and feeds results back to the model automatically. Clients do not need to implement client-side tool loops.
* **Smart Model Routing**: Route requests automatically via `nvirya-auto`, `nvirya-code`, `nvirya-analysis`, or `nvirya-fast` with upstream fallback resilience.
* **Shared-Hosting Architecture**: Zero requirements for Redis, PostgreSQL, Docker, or Kubernetes. Uses SQLite in WAL mode and in-process rate limiting.
* **Multi-Layer Security**: Strict SSRF defenses, AST-based calculator evaluation, path traversal blocks, and prompt injection isolation.
* **Task Quotas & Rate Limits**: 1 request/min per API key and 30 tasks/day per user (resetting at 00:00 `Asia/Ho_Chi_Minh`).
* **Artifacts & File Management**: Task-scoped workspace with isolated storage and authenticated artifact retrieval.
* **Full Streaming Support**: SSE streaming (`stream: true`) with standard OpenAI chunk formatting.

---

## Architecture

```text
[Client Request]
       ↓
[Auth & Rate Limit & Daily Quota]
       ↓
[Model Router (Intent classification / Fallback)]
       ↓
[Agent Orchestrator] <---> [xKiro Provider (api.xkiro.com)]
       ↓
[Tool Execution (Calculator / Web Fetch / Search / Artifacts)]
       ↓
[Final Response / SSE Stream / Artifact Persistence]
```

---

## Supported Endpoints

### OpenAI-Compatible
* `GET  /v1/models` — List available model aliases
* `POST /v1/chat/completions` — Synchronous and SSE streaming chat completions

### Nvirya Agent Endpoints
* `POST /v1/tasks` — Create asynchronous agent task
* `GET  /v1/tasks/{task_id}` — Retrieve task state and result
* `GET  /v1/tasks/{task_id}/events` — Stream task progress events (SSE)
* `POST /v1/tasks/{task_id}/cancel` — Cancel active task
* `GET  /v1/artifacts/{artifact_id}` — Download generated file
* `GET  /v1/quota` — Check daily remaining task quota
* `GET  /v1/usage` — Check user request and token totals

### API Key Management
* `POST   /v1/api-keys` — Generate new API key
* `GET    /v1/api-keys` — List API keys for user
* `DELETE /v1/api-keys/{key_id}` — Revoke an API key

### Health
* `GET /health` — Liveness check
* `GET /ready` — Readiness check (verifies SQLite and storage)

---

## Quickstart (Local Development)

### 1. Install Dependencies
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
```
Ensure your `XKIRO_API_KEY` (or `XKIRO_API`) is populated in `.env`.

### 3. Initialize Database
```bash
python scripts/init_db.py
```
This generates your first admin API key (e.g. `nv-58756a151e46c3cb5d343ba26a9f0be0905300cfddec77b1`).

### 4. Run Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Run Tests
```bash
pytest -v
```

---

## Example Usage

### Python (using `openai` SDK)

```python
from openai import OpenAI

client = OpenAI(
    api_key="nv-58756a151e46c3cb5d343ba26a9f0be0905300cfddec77b1",
    base_url="http://localhost:8000/v1",
)

response = client.chat.completions.create(
    model="nvirya-auto",
    messages=[
        {"role": "user", "content": "What is 345 * 28? Use calculator tool."}
    ],
)

print(response.choices[0].message.content)
# Output: "The result of 345 * 28 is 9660."
```

### cURL

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer nv-58756a151e46c3cb5d343ba26a9f0be0905300cfddec77b1" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nvirya-auto",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": false
  }'
```

---

## Limitations & Operational Boundaries

* **Shared-Hosting Target**: Background processes rely on in-process `asyncio` tasks rather than external queue workers (Celery/Redis).
* **Code Execution**: Generic shell/host command execution is disabled for security. Sandboxed code execution requires a dedicated container sandbox in a VPS environment.
* **Search Backend**: Web search requires a reachable `SEARXNG_URL`. When unconfigured, search cleanly reports unavailable.
* **Browser Rendering**: Headless browser automation (Playwright) is not bundled in the shared-hosting build. Web fetching uses async HTTP (`httpx`) with SSRF filtering.
* **Vision / Audio**: Multimodal endpoints (`nvirya-vision`, Whisper) are structured in the interface layer and planned for future releases.

---

## Documentation

* [API Specification](docs/API.md)
* [System Architecture](docs/ARCHITECTURE.md)
* [Deployment Guide](docs/DEPLOYMENT.md)
* [Model Catalog](docs/MODELS.md)
* [Agent Rules](AGENTS.md)
