# Nvirya AI — Model Configuration & Catalog

## 1. Public Model Aliases

Nvirya AI exposes unified public aliases to client applications while managing internal routing, capability checks, and fallbacks to upstream providers.

| Model Alias | Purpose | Primary Upstream Model | Fallback Model |
| :--- | :--- | :--- | :--- |
| `nvirya-auto` | Heuristic router: auto-detects coding, research, or chat intent | Resolved dynamically | `CODE_MODEL` |
| `nvirya-code` | Software development, tool calling, code generation | `qwen/qwen3.8-max:free` | `mistralai/codestral-2508` |
| `nvirya-analysis`| Long-context research, page synthesis, multi-source summaries | `google/gemini-3.8-flash` | `qwen/qwen3.8-max:free` |
| `nvirya-fast` | Lightweight low-latency queries | `qwen/qwen3.7-flash:free` | `qwen/qwen3.8-max:free` |
| `nvirya-vision` | Visual reasoning and image understanding | *(Planned)* | N/A |

---

## 2. Upstream xKiro Catalog Mapping

Nvirya AI validates configured model IDs against the authoritative xKiro `/v1/models` catalog. Tested upstream models include:

### Coding & Tool Models
* `qwen/qwen3.8-max:free`: 1M context window, native tool-calling and reasoning support.
* `mistralai/codestral-2508`: 256K context window, low-latency code generation.
* `mistralai/devstral-medium`: 256K context, agentic code generation.

### Analysis & Synthesis Models
* `google/gemini-3.8-flash`: Large context reasoning and multi-source synthesis.
* `qwen/qwen3.8-omni-flash:free`: 1M context window.

### Fast / Small Models
* `qwen/qwen3.7-flash:free`: Rapid response model for short conversational turns.
* `mistralai/mistral-small-2603`: Compact hybrid reasoning model.

---

## 3. Dynamic Health Checking & Fallback Policy

The provider adapter tracks the health of upstream models:
* If a model fails 3 consecutive times within 2 minutes, it is marked as degraded.
* The model router automatically routes subsequent requests to the configured fallback model (e.g. `CODE_FALLBACK_MODEL`).
* Once the primary model succeeds again or cooldown expires, normal routing resumes.
