# Nvirya AI — Architecture & Design

## 1. Overview

Nvirya AI is a lightweight, production-oriented AI API Gateway and server-side Agent Runtime built with FastAPI. It translates standard OpenAI-compatible requests into agentic workflows executing server-side tool loops, model routing, content extraction, and persistent file generation.

```text
               +---------------------------+
               |     Client / SDK / UI     |
               +---------------------------+
                             |
                     HTTP / SSE (POST /v1/chat/completions, etc.)
                             v
               +---------------------------+
               |     FastAPI Middleware    |
               |  (Request ID, Rate Limit, |
               |     Daily Quota Check)    |
               +---------------------------+
                             |
                             v
               +---------------------------+
               |       Model Router        |
               | (Heuristics & Fallbacks)  |
               +---------------------------+
                             |
                             v
               +---------------------------+
               |     Agent Orchestrator    |
               |     & Execution Loop      |
               +---------------------------+
                 /           |           \
                /            |            \
               v             v             v
       +-------------+ +-------------+ +-------------+
       |   xKiro     | | Local Tools | |  Storage &  |
       |  Provider   | | (Search,    | |  SQLite DB  |
       |  (Upstream) | |  Fetch,     | | (Quota,     |
       |             | |  Calc,      | |  Tasks,     |
       |             | |  Artifacts) | |  Artifacts) |
       +-------------+ +-------------+ +-------------+
```

---

## 2. Shared-Hosting Principles

Designed specifically to operate on constrained environments (e.g., cPanel, Passenger, basic Python virtual environments):
* **Zero external services required**: No Redis, PostgreSQL, Docker, or Kubernetes dependencies.
* **SQLite in WAL mode**: High-performance single-file relational database with concurrency support.
* **In-process sliding-window rate limiting**: 1 req/min per API key without requiring Redis.
* **In-request & lightweight asyncio execution**: Avoids long-lived Celery worker daemons.

---

## 3. Security Boundaries

* **SSRF Protection**: `WebFetcher` resolves DNS before request dispatch and blocks localhost, 127.0.0.1, private IPv4/IPv6 ranges, link-local addresses, and cloud metadata (169.254.169.254). Strict redirect verification prevents open redirect attacks.
* **Sandboxed Calculator**: Custom Python AST visitor evaluating math expressions without `eval()` or `exec()`.
* **Artifact Path Isolation**: All artifact and temporary file operations enforce strict relative path resolution, blocking traversal tricks (`../`, `..\`, null bytes, Windows drive roots).
* **Prompt Injection Defense**: System prompts enforce separation of concerns between System Policy, User Query, and Untrusted External Tool Data.

---

## 4. Migration to VPS Production

When migrating from shared hosting to a dedicated Linux VPS:
* SQLite can be swapped for PostgreSQL by updating `DATABASE_URL`.
* Rate limiter can transition to Redis backend via the limiter interface.
* SearXNG can point to a private instance via `SEARXNG_URL`.
* Async tasks can utilize a worker queue if task durations exceed web timeout limits.
