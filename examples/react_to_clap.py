"""Dash reacts to claps with a random sound and color change."""

import asyncio
import random

from dash_robot import discover_and_connect

COLORS = ["red", "orange", "yellow", "green", "cyan", "blue", "purple", "magenta", "white"]
SOUNDS = ["hi", "wee", "tada", "okay", "elephant", "cat", "dog", "dino", "laser", "beep"]


async def main():
    robot = await discover_and_connect()
    try:
        print("Listening for claps... (Ctrl+C to stop)")
        await robot.say("hi")
        await robot.all_lights("green")
        last_clap = False

        while True:
            if robot.heard_clap and not last_clap:
                color = random.choice(COLORS)
                sound = random.choice(SOUNDS)
                print(f"  Clap! → {sound} + {color}")
                await robot.all_lights(color)
                await robot.say(sound)
                await robot.head_yaw(random.randint(-40, 40))
                await asyncio.sleep(0.5)
                await robot.head_yaw(0)
            last_clap = robot.heard_clap
            await asyncio.sleep(0.05)
    except KeyboardInterrupt:
        print("\nBye!")
    finally:
        await robot.say("bye")
        await robot.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
