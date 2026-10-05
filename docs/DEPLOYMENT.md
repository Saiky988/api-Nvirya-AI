# Nvirya AI — Deployment Guide

## 1. Local Development Setup

### Prerequisites
* Python 3.11+
* pip

### Installation Steps
1. Clone the repository and enter the directory:
   ```bash
   cd nvirya-ai
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux/macOS:
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env and supply your XKIRO_API_KEY
   ```

5. Initialize SQLite database and generate initial admin API key:
   ```bash
   python scripts/init_db.py
   ```

6. Start the local server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

7. Verify health:
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/ready
   ```

---

## 2. Shared Hosting Deployment (cPanel / Passenger)

Nvirya AI is specifically engineered to run in resource-constrained shared-hosting environments without Docker, Redis, or PostgreSQL.

### cPanel / "Setup Python App" Instructions

1. **Upload Code**:
   Upload the repository files to your application directory (e.g. `/home/username/nvirya-ai`). Ensure `storage/` is writable (`chmod 755 storage`).

2. **Configure Python App in cPanel**:
   * **Python Version**: Select `Python 3.11` or newer.
   * **Application root**: `nvirya-ai`
   * **Application startup file**: `passenger_wsgi.py`
   * **Application Entry point**: `application`

3. **Create `passenger_wsgi.py` (if required by your host)**:
   ```python
   import sys
   import os
   sys.path.insert(0, os.path.dirname(__file__))

   # If host uses asgi-to-wsgi adapter:
   from app.main import app
   from a2wsgi import ASGIMiddleware
   application = ASGIMiddleware(app)
   ```

4. **Install Dependencies in Virtual Environment**:
   Inside cPanel Terminal or SSH:
   ```bash
   source /home/username/virtualenv/nvirya-ai/3.11/bin/activate
   pip install -r requirements.txt
   ```

5. **Initialize Database**:
   ```bash
   python scripts/init_db.py
   ```

6. **Permissions**:
   Ensure the web server process has read/write permissions to:
   * `storage/`
   * `storage/artifacts/`
   * `storage/temp/`
   * `storage/nvirya.db`

---

## 3. Environment Variables Reference

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `APP_NAME` | `Nvirya AI` | Application name |
| `APP_ENV` | `production` | Environment mode (`production`, `testing`) |
| `API_PREFIX` | `/v1` | Root API route prefix |
| `DATABASE_URL` | `sqlite:///./storage/nvirya.db` | SQLite connection URL |
| `XKIRO_BASE_URL` | `https://api.xkiro.com/v1` | Upstream xKiro API endpoint |
| `XKIRO_API_KEY` | *(Required)* | Upstream provider API key |
| `CODE_MODEL` | `qwen/qwen3.8-max:free` | Default model for coding & tools |
| `CODE_FALLBACK_MODEL` | `mistralai/codestral-2508` | Fallback model if primary fails |
| `ANALYSIS_MODEL` | `google/gemini-3.8-flash` | Model for research synthesis |
| `FAST_MODEL` | `qwen/qwen3.7-flash:free` | Fast model for short queries |
| `DAILY_TASK_LIMIT` | `30` | Daily generation quota per user |
| `RATE_LIMIT_PER_MINUTE` | `1` | Request rate limit per API key |
| `MAX_AGENT_STEPS` | `8` | Maximum tool execution turns |
| `MAX_TOOL_CALLS_PER_TASK` | `8` | Maximum tool calls per task |
| `MAX_TASK_SECONDS` | `120` | Timeout budget per task |
| `SEARXNG_URL` | *(Optional)* | Remote SearXNG search endpoint |

---

## 4. Operational Limitations

* **Shared-Hosting Constraints**: CPU and memory limits are enforced by the host. Tasks run with bounded budgets (`MAX_TASK_SECONDS=120`).
* **Search Capability**: Web search requires `SEARXNG_URL`. When unconfigured, search reports a structured "search unavailable" tool response.
* **Code Execution**: Direct host shell command execution is prohibited for security. Sandboxed code execution is reserved for future containerized environments.
