"""Cycle through rainbow colors on all LEDs."""

import asyncio

from dash_robot import discover_and_connect

COLORS = ["red", "orange", "yellow", "green", "cyan", "blue", "purple", "magenta"]


async def main():
    robot = await discover_and_connect()
    try:
        print("Starting lightshow...")
        await robot.say("wee")
        for _ in range(3):
            for color in COLORS:
                await robot.neck_color(color)
                await robot.left_ear_color(color)
                await robot.right_ear_color(color)
                await asyncio.sleep(0.3)
        await robot.all_lights("white")
        await robot.say("tada")
    finally:
        await robot.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
