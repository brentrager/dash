import asyncio
import time
from collections import defaultdict

from bleak import BleakClient

from dash_robot.constants import DASH_SENSOR_CHAR_UUID, DOT_SENSOR_CHAR_UUID


def _to_int(value: int, bits: int) -> int:
    if value > ((1 << (bits - 1)) - 1):
        return value - (1 << bits)
    return value


class Sensors:
    """Subscribes to Dash's two BLE sensor streams and decodes them into a dict."""

    def __init__(self, client: BleakClient, state: defaultdict):
        self.client = client
        self.state = state
        self.dot_ready = False
        self.dash_ready = False

    async def start(self, timeout: float = 1.0):
        await self.client.start_notify(DOT_SENSOR_CHAR_UUID, self._decode_dot)
        await self.client.start_notify(DASH_SENSOR_CHAR_UUID, self._decode_dash)
        await asyncio.sleep(timeout)

        if self.dash_ready and self.dot_ready:
            self.state["robot"] = "dash"
        elif self.dot_ready:
            self.state["robot"] = "dot"
        else:
            raise RuntimeError(f"No sensor data received within {timeout}s")

    async def stop(self):
        await self.client.stop_notify(DOT_SENSOR_CHAR_UUID)
        await self.client.stop_notify(DASH_SENSOR_CHAR_UUID)

    def _decode_dot(self, _handle: object, value: bytearray) -> None:
        self.dot_ready = True
        s = self.state
        s["time"] = time.time()
        s["pitch"] = _to_int((value[4] & 0xF0) << 4 | value[2], 12)
        s["roll"] = _to_int((value[4] & 0x0F) << 8 | value[3], 12)
        s["acceleration"] = _to_int((value[5] & 0xF0) << 4 | value[6], 12)
        s["button_main"] = bool(value[8] & 0x10)
        s["button_1"] = bool(value[8] & 0x20)
        s["button_2"] = bool(value[8] & 0x40)
        s["button_3"] = bool(value[8] & 0x80)
        s["moving"] = value[11] == 0
        s["picked_up"] = bool(value[11] & 0x04)
        s["hit"] = bool(value[11] & 0x01)
        s["on_side"] = value[11] & 0x20 == 0x20
        s["clap"] = bool(value[11] & 0x01)
        s["mic_level"] = value[7]
        if value[15] == 4:
            s["sound_direction"] = value[13] << 8 | value[12]

    def _decode_dash(self, _handle: object, value: bytearray) -> None:
        self.dash_ready = True
        s = self.state
        s["dash_time"] = time.time()
        s["pitch_delta"] = _to_int((value[4] & 0x30) << 4 | value[3], 10)
        s["roll_delta"] = _to_int((value[4] & 0x03) << 8 | value[5], 10)
        s["prox_right"] = value[6]
        s["prox_left"] = value[7]
        s["prox_rear"] = value[8]
        yaw = _to_int((value[13] << 8) | value[12], 12)
        s["yaw_delta"] = yaw - s["yaw"]
        s["yaw"] = yaw
        s["left_wheel"] = (value[15] << 8) | value[14]
        s["right_wheel"] = (value[17] << 8) | value[16]
        s["head_pitch"] = value[18]
        s["head_yaw"] = value[19]
        s["wheel_distance"] = _to_int((value[9] & 0x0F) << 12 | value[11] << 8 | value[10], 16)
