# Agent Rules & Guidelines

- Inspect existing code before modifying.
- Preserve working architecture.
- Do not rewrite unrelated files.
- Keep modules small.
- Avoid unnecessary dependencies.
- Do not add Docker/Redis/Postgres requirements to the shared-host MVP.
- Never commit secrets.
- Never create .env with real credentials.
- Never use eval/exec for untrusted input.
- Never execute model-generated shell commands on the host.
- Do not weaken SSRF protections.
- Write tests for every new core behavior.
- Prefer a working implementation over speculative abstractions.
- Keep comments minimal.
