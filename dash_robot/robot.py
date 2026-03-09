import asyncio
import logging
import struct
from collections import defaultdict

from bleak import BleakClient, BleakScanner
from colour import Color

from dash_robot.constants import COMMAND_CHAR_UUID, COMMANDS, NOISES, ROBOT_SERVICE_UUID
from dash_robot.sensors import Sensors

log = logging.getLogger(__name__)


def _one_byte(value: int) -> bytearray:
    return bytearray(struct.pack(">B", value))


def _two_bytes(value: int) -> bytearray:
    return bytearray(struct.pack(">H", value))


def _color_bytes(color_value: str) -> bytearray:
    c = Color(color_value)
    return bytearray(
        [
            int(round(c.get_red() * 255)),
            int(round(c.get_green() * 255)),
            int(round(c.get_blue() * 255)),
        ]
    )


def _angle_byte(angle: int) -> bytearray:
    if angle < 0:
        angle = (abs(angle) ^ 0xFF) + 1
    return bytearray([angle & 0xFF])


async def discover(timeout: float = 5.0) -> str | None:
    """Scan for a Dash/Dot robot by service UUID and return its BLE address."""
    devices = await BleakScanner.discover(timeout=timeout, service_uuids=[str(ROBOT_SERVICE_UUID)])
    for d in devices:
        log.info("Found robot at %s (%s)", d.address, d.name or "unnamed")
        return d.address
    return None


async def discover_and_connect(timeout: float = 5.0) -> "DashRobot":
    """Scan, connect, and return a ready-to-use DashRobot."""
    address = await discover(timeout)
    if not address:
        raise RuntimeError("No Dash robot found. Is it turned on?")
    robot = DashRobot(address)
    await robot.connect()
    return robot


class DashRobot:
    """High-level async controller for Wonder Workshop's Dash robot."""

    def __init__(self, address: str):
        self.address = address
        self.client: BleakClient | None = None
        self.sensors: Sensors | None = None
        self.state: defaultdict[str, int | float | bool] = defaultdict(int)

    # ── Connection ──────────────────────────────────────────────

    async def connect(self):
        self.client = BleakClient(self.address)
        await self.client.connect()
        log.info("Connected to %s", self.address)
        self.sensors = Sensors(self.client, self.state)
        await self.sensors.start()

    async def disconnect(self):
        if self.client and self.client.is_connected:
            if self.sensors:
                await self.sensors.stop()
            await self.client.disconnect()
            log.info("Disconnected from %s", self.address)

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *exc):
        await self.disconnect()

    # ── Low-level ───────────────────────────────────────────────

    async def _cmd(self, name: str, payload: bytearray):
        assert self.client and self.client.is_connected
        message = bytearray([COMMANDS[name]]) + payload
        await self.client.write_gatt_char(COMMAND_CHAR_UUID, message)

    # ── Lights ──────────────────────────────────────────────────

    async def neck_color(self, color: str):
        """Set neck LED. Accepts any CSS color name or hex (e.g. 'red', '#ff0000')."""
        await self._cmd("neck_color", _color_bytes(color))

    async def left_ear_color(self, color: str):
        await self._cmd("left_ear_color", _color_bytes(color))

    async def right_ear_color(self, color: str):
        await self._cmd("right_ear_color", _color_bytes(color))

    async def ear_color(self, color: str):
        """Set both ears to the same color."""
        await self.left_ear_color(color)
        await self.right_ear_color(color)

    async def eye(self, value: int):
        """Set eye pattern (12-bit bitmask for the 12 LEDs)."""
        await self._cmd("eye", _two_bytes(value))

    async def eye_brightness(self, value: int):
        """Set eye brightness (0–255)."""
        await self._cmd("eye_brightness", _one_byte(max(0, min(255, value))))

    async def tail_brightness(self, value: int):
        """Set tail light brightness (0–255)."""
        await self._cmd("tail_brightness", _one_byte(max(0, min(255, value))))

    async def all_lights(self, color: str, brightness: int = 255):
        """Set all LEDs to one color at full brightness."""
        await self.neck_color(color)
        await self.ear_color(color)
        await self.eye_brightness(brightness)
        await self.tail_brightness(brightness)

    # ── Head ────────────────────────────────────────────────────

    async def head_yaw(self, angle: int):
        """Turn head left/right. Range: -53 to 53 degrees."""
        await self._cmd("head_yaw", _angle_byte(max(-53, min(53, angle))))

    async def head_pitch(self, angle: int):
        """Tilt head up/down. Range: -5 to 10 degrees."""
        await self._cmd("head_pitch", _angle_byte(max(-5, min(10, angle))))

    async def look(self, yaw: int = 0, pitch: int = 0):
        """Move head to a specific yaw and pitch."""
        await self.head_yaw(yaw)
        await self.head_pitch(pitch)

    # ── Sound ───────────────────────────────────────────────────

    async def say(self, sound_name: str):
        """Play a built-in sound. See NOISES dict for available names."""
        if sound_name not in NOISES:
            raise ValueError(
                f"Unknown sound '{sound_name}'. Available: {', '.join(sorted(NOISES))}"
            )
        await self._cmd("say", bytearray(NOISES[sound_name]))

    # ── Movement ────────────────────────────────────────────────

    async def drive(self, speed: int):
        """Drive forward (positive) or backward (negative). Range: -2048 to 2048."""
        speed = max(-2048, min(2048, speed))
        if speed < 0:
            speed = 0x800 + speed  # two's complement 12-bit
        await self._cmd("drive", bytearray([speed & 0xFF, 0x00, (speed & 0x0F00) >> 8]))

    async def spin(self, speed: int):
        """Spin in place. Positive = clockwise, negative = counter-clockwise."""
        speed = max(-2048, min(2048, speed))
        if speed < 0:
            speed = 0x800 + speed  # two's complement 12-bit
        await self._cmd("drive", bytearray([0x00, speed & 0xFF, (speed & 0x0F00) >> 8]))

    async def stop(self):
        """Stop all movement."""
        await self._cmd("drive", bytearray([0, 0, 0]))

    async def move(self, distance_mm: int, speed_mmps: int = 1000):
        """Move a specific distance in mm, then stop. Negative = backward."""
        speed_mmps = abs(speed_mmps)
        seconds = abs(distance_mm / speed_mmps)

        eight_byte = 0x81 if distance_mm < 0 else 0x80
        dist_low = distance_mm & 0xFF
        dist_high = (distance_mm >> 8) & 0x3F
        time_ms = int(seconds * 1000)

        payload = bytearray(
            [
                dist_low,
                0x00,
                0x00,
                (time_ms >> 8) & 0xFF,
                time_ms & 0xFF,
                dist_high,
                0x00,
                eight_byte,
            ]
        )
        await self._cmd("move", payload)
        await asyncio.sleep(seconds)

    async def turn(self, degrees: int, speed_dps: float = 172.0):
        """Turn a specific number of degrees. Positive = clockwise."""
        if abs(degrees) > 360:
            raise ValueError("Cannot turn more than 360 degrees per move")
        speed = 200 if degrees > 0 else -200
        duration = abs(degrees / speed_dps)
        await self.spin(speed)
        await asyncio.sleep(duration)
        await self.stop()

    # ── Reset ───────────────────────────────────────────────────

    async def reset(self, mode: int = 4):
        """Reset the robot. Mode 4 = soft reset."""
        await self._cmd("reset", bytearray([mode]))

    # ── Sensor shortcuts ────────────────────────────────────────

    @property
    def proximity(self) -> dict[str, int | float]:
        return {
            "left": self.state["prox_left"],
            "right": self.state["prox_right"],
            "rear": self.state["prox_rear"],
        }

    @property
    def is_picked_up(self) -> bool:
        return bool(self.state["picked_up"])

    @property
    def heard_clap(self) -> bool:
        return bool(self.state["clap"])

    @property
    def buttons(self) -> dict[str, bool]:
        return {
            "main": bool(self.state["button_main"]),
            "1": bool(self.state["button_1"]),
            "2": bool(self.state["button_2"]),
            "3": bool(self.state["button_3"]),
        }
