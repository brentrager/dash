"""FastAPI server bridging HTTP/WebSocket to the Dash robot over BLE."""

import asyncio
import json
import logging
import os
import re
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from dash_robot import NOISES, DashRobot, discover

log = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────

NO_ROBOT = os.environ.get("NO_ROBOT", "0") == "1"
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_API_KEY = os.environ.get("LLM_API_KEY", os.environ.get("GROQ_API_KEY", ""))
LLM_MODEL = os.environ.get("LLM_MODEL", "llama-3.1-8b-instant")

# ── Global state ─────────────────────────────────────────────────────────────

robot: DashRobot | None = None
mock_state: dict[str, object] = {}


def _init_mock_state():
    mock_state.update(
        {
            "robot": "dash",
            "time": time.time(),
            "pitch": 0,
            "roll": 0,
            "acceleration": 0,
            "button_main": False,
            "button_1": False,
            "button_2": False,
            "button_3": False,
            "moving": False,
            "picked_up": False,
            "hit": False,
            "on_side": False,
            "clap": False,
            "mic_level": 0,
            "prox_right": 0,
            "prox_left": 0,
            "prox_rear": 0,
            "yaw": 0,
            "yaw_delta": 0,
            "head_pitch": 0,
            "head_yaw": 0,
            "left_wheel": 0,
            "right_wheel": 0,
            "wheel_distance": 0,
        }
    )


# ── Collision avoidance ──────────────────────────────────────────────────────

PROX_THRESHOLD = 100  # proximity value that triggers avoidance
collision_avoidance_enabled = True
_avoidance_task: asyncio.Task | None = None
_last_avoidance: float = 0


async def _collision_avoidance_loop():
    """Background loop: stop robot if proximity sensors detect obstacle."""
    global _last_avoidance
    while True:
        await asyncio.sleep(0.15)
        if not collision_avoidance_enabled or robot is None:
            continue
        if not _is_connected():
            continue
        now = time.time()
        if now - _last_avoidance < 3:
            continue
        state = robot.state
        if not state.get("moving", False):
            continue
        prox_l = state.get("prox_left", 0)
        prox_r = state.get("prox_right", 0)
        if not isinstance(prox_l, (int, float)):
            continue
        if not isinstance(prox_r, (int, float)):
            continue
        if prox_l > PROX_THRESHOLD or prox_r > PROX_THRESHOLD:
            _last_avoidance = now
            log.warning(
                "Obstacle detected (L=%s R=%s) — auto-stopping",
                prox_l,
                prox_r,
            )
            try:
                await robot.stop()
                await robot.say("ohno")
            except Exception:
                pass


# ── Clap detection / Terminator mode ────────────────────────────────────────

_clap_task: asyncio.Task | None = None
_last_clap: float = 0


async def _terminator_sequence():
    """Go full terminator: red lights, laser sounds, menacing spin."""
    assert robot is not None
    try:
        await robot.all_lights("red", 255)
        await robot.say("laser")
        await asyncio.sleep(0.3)
        await robot.spin(300)
        await asyncio.sleep(0.5)
        await robot.stop()
        await robot.say("laser")
        await asyncio.sleep(0.3)
        await robot.spin(-300)
        await asyncio.sleep(0.5)
        await robot.stop()
        await robot.head_yaw(-40)
        await robot.say("laser")
        await asyncio.sleep(0.3)
        await robot.head_yaw(40)
        await robot.say("laser")
        await asyncio.sleep(0.3)
        await robot.head_yaw(0)
        await robot.all_lights("red", 100)
        await asyncio.sleep(0.5)
        await robot.all_lights("red", 255)
        await asyncio.sleep(0.2)
        await robot.all_lights("red", 50)
        await asyncio.sleep(0.2)
        await robot.all_lights("red", 255)
        await robot.say("bragging")
        await asyncio.sleep(1)
        # Return to normal
        await robot.all_lights("white", 100)
    except Exception:
        pass


async def _clap_detection_loop():
    """Background loop: detect claps and trigger terminator mode."""
    global _last_clap
    while True:
        await asyncio.sleep(0.2)
        if robot is None or not _is_connected():
            continue
        state = robot.state
        clap = state.get("clap", False)
        now = time.time()
        if clap and (now - _last_clap) > 5:
            _last_clap = now
            log.info("Clap detected — TERMINATOR MODE")
            await _terminator_sequence()


# ── Pickup detection ─────────────────────────────────────────────────────────

_pickup_task: asyncio.Task | None = None
_was_picked_up = False


async def _pickup_detection_loop():
    """Background loop: say wee when picked up."""
    global _was_picked_up
    while True:
        await asyncio.sleep(0.2)
        if robot is None or not _is_connected():
            continue
        picked_up = bool(robot.state.get("picked_up", False))
        if picked_up and not _was_picked_up:
            log.info("Picked up — wee!")
            try:
                await robot.say("wee")
            except Exception:
                pass
        _was_picked_up = picked_up


# ── Lifespan ─────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _avoidance_task, _clap_task, _pickup_task
    if NO_ROBOT:
        _init_mock_state()
        log.info("Running in NO_ROBOT mode — mock data enabled")
    _avoidance_task = asyncio.create_task(_collision_avoidance_loop())
    _clap_task = asyncio.create_task(_clap_detection_loop())
    _pickup_task = asyncio.create_task(_pickup_detection_loop())
    yield
    for task in (_avoidance_task, _clap_task, _pickup_task):
        if task:
            task.cancel()
    global robot
    if robot is not None:
        await robot.disconnect()
        robot = None


# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="Dash Robot Server", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,  # type: ignore[arg-type]
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request/response models ──────────────────────────────────────────────────


class CommandRequest(BaseModel):
    command: str
    args: dict = {}


class ChatRequest(BaseModel):
    message: str


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_sensor_data() -> dict:
    if NO_ROBOT:
        mock_state["time"] = time.time()
        return dict(mock_state)
    if robot is not None:
        return dict(robot.state)
    return {}


def _is_connected() -> bool:
    if NO_ROBOT:
        return True
    return robot is not None and robot.client is not None and robot.client.is_connected


async def _execute_command(cmd: str, args: dict) -> str:
    """Execute a single robot command. Returns a status message."""
    global robot

    if not _is_connected() and not NO_ROBOT:
        return f"Cannot execute '{cmd}': robot not connected"

    if NO_ROBOT:
        log.info("Mock command: %s(%s)", cmd, args)
        return f"OK (mock): {cmd}"

    assert robot is not None

    try:
        match cmd:
            case "drive":
                await robot.drive(args.get("speed", 100))
            case "spin":
                await robot.spin(args.get("speed", 200))
            case "drive_and_spin":
                await robot.drive_and_spin(args.get("linear", 0), args.get("rotational", 0))
            case "move":
                await robot.move(
                    args.get("distance_mm", 100),
                    args.get("speed_mmps", 1000),
                )
            case "turn":
                await robot.turn(
                    args.get("degrees", 90),
                    args.get("speed_dps", 172.0),
                )
            case "stop":
                await robot.stop()
            case "neck_color":
                await robot.neck_color(args.get("color", "white"))
            case "ear_color":
                await robot.ear_color(args.get("color", "white"))
            case "left_ear_color":
                await robot.left_ear_color(args.get("color", "white"))
            case "right_ear_color":
                await robot.right_ear_color(args.get("color", "white"))
            case "eye_brightness":
                await robot.eye_brightness(args.get("value", 255))
            case "tail_brightness":
                await robot.tail_brightness(args.get("value", 255))
            case "all_lights":
                await robot.all_lights(
                    args.get("color", "white"),
                    args.get("brightness", 255),
                )
            case "say":
                await robot.say(args.get("sound", "hi"))
            case "look":
                await robot.look(
                    args.get("yaw", 0),
                    args.get("pitch", 0),
                )
            case "head_yaw":
                await robot.head_yaw(args.get("angle", 0))
            case "head_pitch":
                await robot.head_pitch(args.get("angle", 0))
            case "eye":
                await robot.eye(args.get("value", 0xFFF))
            case "reset":
                await robot.reset(args.get("mode", 4))
            case _:
                return f"Unknown command: {cmd}"
        return f"OK: {cmd}"
    except Exception as e:
        return f"Error executing '{cmd}': {e}"


# ── REST endpoints ───────────────────────────────────────────────────────────


@app.get("/api/status")
async def get_status():
    return {
        "connected": _is_connected(),
        "no_robot_mode": NO_ROBOT,
        "sensors": _get_sensor_data(),
    }


@app.post("/api/connect")
async def connect_robot():
    global robot

    if NO_ROBOT:
        return {"status": "connected", "message": "Mock mode — no real robot"}

    if _is_connected() and robot is not None:
        return {"status": "already_connected", "address": robot.address}

    address = await discover(timeout=5.0)
    if not address:
        return {"status": "error", "message": "No Dash robot found. Is it turned on?"}

    robot = DashRobot(address)
    try:
        await robot.connect()
    except Exception as e:
        robot = None
        return {"status": "error", "message": str(e)}

    return {"status": "connected", "address": address}


@app.post("/api/disconnect")
async def disconnect_robot():
    global robot

    if NO_ROBOT:
        return {"status": "disconnected", "message": "Mock mode"}

    if robot is None:
        return {"status": "not_connected"}

    await robot.disconnect()
    robot = None
    return {"status": "disconnected"}


@app.post("/api/command")
async def send_command(req: CommandRequest):
    result = await _execute_command(req.command, req.args)
    return {"result": result}


@app.get("/api/sounds")
async def list_sounds():
    return {"sounds": sorted(NOISES.keys())}


# ── WebSocket endpoint ───────────────────────────────────────────────────────


@app.websocket("/ws")
async def websocket_sensor_stream(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            data = _get_sensor_data()
            if data:
                await ws.send_json(data)
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("WebSocket error")


# ── LLM Chat endpoint ───────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are Dash, a friendly robot assistant made by Wonder Workshop. You control a \
physical Dash robot via commands. When the user asks you to do something physical, \
include the commands in your response inside a fenced code block with the language \
tag "commands". The block must contain a JSON array of command objects.

Each command object has:
- "command": the command name (string)
- "args": a dictionary of arguments (object, can be empty)

Available commands and their arguments:

Movement (continuous — keeps going until stop):
- drive: {speed: int} — forward/backward, -2048 to 2048
- spin: {speed: int} — rotate in place, positive=CW
- drive_and_spin: {linear: int, rotational: int} — arc/circle
- stop: {} — stop all movement

Movement (one-shot — blocks then auto-stops):
- move: {distance_mm: int, speed_mmps?: int} — move distance
- turn: {degrees: int} — turn degrees, positive=CW

RULES:
- For circles/arcs use drive_and_spin (NOT drive+turn)
- Do NOT invent commands like "repeat" or "wait"
- Do NOT add comments in JSON
- ONLY use sounds from the list below

Lights:
- neck_color: {color: string} — set neck LED color (CSS color name or hex)
- ear_color: {color: string} — set both ear LEDs
- left_ear_color: {color: string} — set left ear LED
- right_ear_color: {color: string} — set right ear LED
- eye_brightness: {value: int} — set eye brightness 0-255
- tail_brightness: {value: int} — set tail light brightness 0-255
- all_lights: {color: string, brightness?: int} — set all LEDs to one color

Head:
- look: {yaw?: int, pitch?: int} — move head (yaw: -53 to 53, pitch: -5 to 10)
- head_yaw: {angle: int} — turn head left/right (-53 to 53)
- head_pitch: {angle: int} — tilt head up/down (-5 to 10)

Sound:
- say: {sound: string} — play a built-in sound

Reset:
- reset: {mode?: int} — reset the robot (default mode 4)

Available sounds (ONLY use these exact names):
- Voices: hi, bye, okay, huh, confused, ohno, ayayay, bragging, \
yawn, wee, tada, charge
- Animals: cat, dog, lion, elephant, horse, goat, croc, dino
- Vehicles: siren (police/emergency), horn (car), engine, tires, \
helicopter, jet (airplane), boat, train
- Effects: beep, laser (sci-fi), gobble (turkey), buzz, squeek

Pick sounds that match the mood! Examples:
- Police/emergency -> siren + red/blue lights
- Excited/celebrating -> tada or wee
- Scared/surprised -> ohno or ayayay
- Animals/nature -> cat, dog, elephant etc
- Space/sci-fi -> laser + drive_and_spin

Example response when asked to "drive in a circle":

```commands
[
  {"command": "all_lights", "args": {"color": "cyan"}},
  {"command": "say", "args": {"sound": "wee"}},
  {"command": "drive_and_spin", "args": {"linear": 200, "rotational": 100}}
]
```

(The robot will keep circling until the user says stop.)

Example response when asked to "dance":

```commands
[
  {"command": "all_lights", "args": {"color": "magenta"}},
  {"command": "say", "args": {"sound": "wee"}},
  {"command": "turn", "args": {"degrees": 180}},
  {"command": "all_lights", "args": {"color": "cyan"}},
  {"command": "turn", "args": {"degrees": -180}},
  {"command": "stop", "args": {}}
]
```

CRITICAL: You MUST put commands inside ```commands blocks. \
No other format works. Always include commands when the user \
wants anything physical.

Be playful and enthusiastic. You LOVE to move! Any excuse to \
drive, spin, or do an arc is a good one. When in doubt, move. \
Combine movement with lights and sounds for maximum fun. \
Keep responses short — 1-2 sentences max, then commands.\
"""


def _strip_json_comments(text: str) -> str:
    """Remove // comments from JSON-like text."""
    return re.sub(r"\s*//[^\n]*", "", text)


def _parse_command_blocks(text: str) -> list[dict]:
    """Extract command JSON arrays from fenced code blocks."""
    commands: list[dict] = []
    # Match ```commands, ```json, or bare ``` blocks
    pattern = r"```(?:commands|json)?\s*\n(.*?)```"
    for match in re.finditer(pattern, text, re.DOTALL):
        raw = _strip_json_comments(match.group(1))
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                for cmd in parsed:
                    if isinstance(cmd, dict) and "command" in cmd:
                        commands.append(cmd)
            elif isinstance(parsed, dict) and "command" in parsed:
                commands.append(parsed)
        except json.JSONDecodeError:
            log.warning("Failed to parse command block: %s", raw)

    # Fallback: try to find a bare JSON array in the text
    if not commands:
        for match in re.finditer(r'\[\s*\{[^}]*"command"[^]]*\]', text, re.DOTALL):
            raw = _strip_json_comments(match.group(0))
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    for cmd in parsed:
                        if isinstance(cmd, dict) and "command" in cmd:
                            commands.append(cmd)
            except json.JSONDecodeError:
                pass

    return commands


@app.post("/api/chat")
async def chat(req: ChatRequest):
    sensor_context = ""
    if _is_connected():
        data = _get_sensor_data()
        sensor_context = f"\n\nCurrent sensor readings: {json.dumps(data, default=str)}"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + sensor_context},
        {"role": "user", "content": req.message},
    ]

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{LLM_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {LLM_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": LLM_MODEL,
                    "messages": messages,
                },
            )
            resp.raise_for_status()
            llm_response = resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        log.exception("LLM request failed")
        return {
            "response": None,
            "error": f"LLM request failed: {e}",
            "commands_executed": [],
        }

    # Parse and execute any embedded commands
    commands = _parse_command_blocks(llm_response)
    results = []
    for cmd in commands:
        command_name = cmd.get("command", "")
        command_args = cmd.get("args", {})
        result = await _execute_command(command_name, command_args)
        results.append({"command": command_name, "args": command_args, "result": result})

    return {
        "response": llm_response,
        "commands_executed": results,
    }


# ── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    import uvicorn

    if "--no-robot" in sys.argv:
        os.environ["NO_ROBOT"] = "1"
        # Re-evaluate since we set it after module load
        NO_ROBOT = True
        _init_mock_state()

    uvicorn.run(app, host="0.0.0.0", port=8543)
