"""Drive Dash in a square pattern."""

import asyncio

from dash_robot import discover_and_connect


async def main():
    robot = await discover_and_connect()
    try:
        print("Driving a square...")
        await robot.say("charge")
        await asyncio.sleep(1)

        for i in range(4):
            print(f"  Side {i + 1}/4")
            await robot.move(300, speed_mmps=200)
            await robot.turn(90)
            await asyncio.sleep(0.3)

        await robot.say("tada")
        print("Done!")
    finally:
        await robot.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
