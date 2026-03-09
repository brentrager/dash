# Dash Robot

Python BLE controller + Next.js dashboard for Wonder Workshop's Dash robot. Vibe-coded with Claude Code.

## Stack
- **Python 3.13**: bleak (BLE), colour (RGB), asyncio, FastAPI, httpx
- **Frontend**: Next.js 16, TypeScript, Tailwind CSS 4
- **LLM**: Groq (llama-3.1-8b-instant) for natural language robot control
- **Python tooling**: uv (not pip), ruff (not black), ty (not mypy)
- **JS/TS tooling**: pnpm (not npm), oxfmt (not prettier), oxlint (not eslint)

## Structure
- `dash_robot/` — library package (connection, commands, sensors, constants)
- `server/` — FastAPI backend bridging HTTP/WebSocket to BLE robot + LLM chat
- `frontend/` — Next.js dashboard (movement, lights, sounds, sensors, AI chat)
- `examples/` — runnable scripts demonstrating robot capabilities
- `cli.py` — interactive CLI for controlling Dash from the terminal

## Commands
```bash
# Run backend (mock mode for dev without robot)
NO_ROBOT=1 uv run python -m server.main

# Run frontend
cd frontend && pnpm dev

# Python format + lint + typecheck
uv run ruff format . && uv run ruff check . && uv run ty check

# Frontend lint + format check
cd frontend && pnpm check
```

## Ports
- Backend: 8543
- Frontend: 3543

## Security
- **NEVER commit secrets**: API keys, tokens must never appear in code. Use env vars.
- Secrets live in `.envrc` (gitignored). Required: `GROQ_API_KEY`.
- Claude hooks auto-scan for secrets before every commit.

## BLE Protocol
- Robot advertises as "Dash" over BLE with service UUID `AF237777-879D-6186-1F49-DECA0E85D9C1`
- Commands sent via GATT write to characteristic `AF230002-879D-6186-1F49-DECA0E85D9C1`
- Two sensor streams (Dash + Dot-compatible) via notify on `AF230006` and `AF230003`
- Command format: first byte = command ID, remaining bytes = payload
