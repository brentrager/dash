# Dash Robot

Python BLE controller for Wonder Workshop's Dash robot. Vibe-coded with Claude Code.

## Stack
- **Python 3.13**: bleak (BLE), colour (RGB), asyncio
- **Tooling**: uv (not pip), ruff (not black), ty (not mypy)

## Structure
- `dash_robot/` — library package (connection, commands, sensors, constants)
- `examples/` — runnable scripts demonstrating robot capabilities
- `cli.py` — interactive CLI for controlling Dash from the terminal

## Commands
```bash
# Run an example
uv run python examples/lightshow.py

# Interactive CLI
uv run python cli.py

# Format + lint
uv run ruff format . && uv run ruff check . && uv run ty check
```

## BLE Protocol
- Robot advertises as "Dash" over BLE with service UUID `AF237777-879D-6186-1F49-DECA0E85D9C1`
- Commands sent via GATT write to characteristic `AF230002-879D-6186-1F49-DECA0E85D9C1`
- Two sensor streams (Dash + Dot-compatible) via notify on `AF230006` and `AF230003`
- Command format: first byte = command ID, remaining bytes = payload
