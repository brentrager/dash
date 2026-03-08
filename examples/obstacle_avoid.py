"""Simple obstacle avoidance using proximity sensors."""

import asyncio

from dash_robot import discover_and_connect

PROX_THRESHOLD = 100  # Higher = closer to obstacle


async def main():
    robot = await discover_and_connect()
    try:
        print("Obstacle avoidance mode (Ctrl+C to stop)")
        await robot.say("charge")
        await robot.neck_color("green")

        while True:
            prox = robot.proximity

            if prox["left"] > PROX_THRESHOLD or prox["right"] > PROX_THRESHOLD:
                # Something ahead — stop, flash red, turn away
                await robot.stop()
                await robot.neck_color("red")
                await robot.say("ohno")

                if prox["left"] > prox["right"]:
                    await robot.turn(90)
                else:
                    await robot.turn(-90)

                await robot.neck_color("green")
            else:
                await robot.drive(150)

            await asyncio.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        await robot.stop()
        await robot.say("bye")
        await robot.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
