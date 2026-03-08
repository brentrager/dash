"""Interactive CLI for controlling Dash from the terminal."""

import asyncio
import shlex

from dash_robot import NOISES, DashRobot, discover_and_connect

HELP = """
Commands:
  connect              Scan and connect to Dash
  disconnect           Disconnect from Dash

  drive <speed>        Drive forward/backward (-2048 to 2048)
  spin <speed>         Spin in place (positive=CW, negative=CCW)
  move <mm> [speed]    Move specific distance in mm
  turn <degrees>       Turn specific degrees
  stop                 Stop all movement

  neck <color>         Set neck LED color (e.g. red, #ff0000)
  ears <color>         Set both ear LEDs
  lights <color>       Set all LEDs to one color
  eye <brightness>     Set eye brightness (0-255)
  tail <brightness>    Set tail brightness (0-255)

  look <yaw> [pitch]   Move head (-53..53 yaw, -5..10 pitch)

  say <sound>          Play a sound (try: hi, tada, cat, laser)
  sounds               List all available sounds

  sensors              Print current sensor readings
  buttons              Print button states

  help                 Show this help
  quit                 Disconnect and exit
""".strip()


async def main():
    robot: DashRobot | None = None

    print("Dash Robot CLI")
    print("Type 'connect' to find your robot, or 'help' for commands.\n")

    while True:
        try:
            line = await asyncio.get_event_loop().run_in_executor(None, lambda: input("dash> "))
        except (EOFError, KeyboardInterrupt):
            break

        line = line.strip()
        if not line:
            continue

        parts = shlex.split(line)
        cmd = parts[0].lower()
        args = parts[1:]

        try:
            if cmd == "help":
                print(HELP)

            elif cmd == "connect":
                if robot:
                    print("Already connected. Use 'disconnect' first.")
                else:
                    print("Scanning for Dash...")
                    robot = await discover_and_connect()
                    print(f"Connected to {robot.address}")

            elif cmd == "disconnect":
                if robot:
                    await robot.disconnect()
                    robot = None
                    print("Disconnected.")
                else:
                    print("Not connected.")

            elif cmd == "quit":
                break

            elif cmd == "sounds":
                print(", ".join(sorted(NOISES.keys())))

            elif not robot:
                print("Not connected. Run 'connect' first.")

            elif cmd == "drive":
                await robot.drive(int(args[0]))
            elif cmd == "spin":
                await robot.spin(int(args[0]))
            elif cmd == "move":
                mm = int(args[0])
                speed = int(args[1]) if len(args) > 1 else 1000
                await robot.move(mm, speed)
            elif cmd == "turn":
                await robot.turn(int(args[0]))
            elif cmd == "stop":
                await robot.stop()

            elif cmd == "neck":
                await robot.neck_color(args[0])
            elif cmd == "ears":
                await robot.ear_color(args[0])
            elif cmd == "lights":
                await robot.all_lights(args[0])
            elif cmd == "eye":
                await robot.eye_brightness(int(args[0]))
            elif cmd == "tail":
                await robot.tail_brightness(int(args[0]))

            elif cmd == "look":
                yaw = int(args[0])
                pitch = int(args[1]) if len(args) > 1 else 0
                await robot.look(yaw, pitch)

            elif cmd == "say":
                await robot.say(args[0])

            elif cmd == "sensors":
                prox = robot.proximity
                print(f"  Proximity: L={prox['left']} R={prox['right']} Rear={prox['rear']}")
                print(f"  Picked up: {robot.is_picked_up}")
                print(f"  Clap: {robot.heard_clap}")
                print(f"  Yaw: {robot.state['yaw']}")
                print(f"  Wheel dist: {robot.state['wheel_distance']}")

            elif cmd == "buttons":
                for name, pressed in robot.buttons.items():
                    print(f"  {name}: {'PRESSED' if pressed else '-'}")

            else:
                print(f"Unknown command: {cmd}. Type 'help' for commands.")

        except (IndexError, ValueError) as e:
            print(f"Bad arguments: {e}. Type 'help' for usage.")
        except Exception as e:
            print(f"Error: {e}")

    if robot:
        await robot.disconnect()
    print("Bye!")


if __name__ == "__main__":
    asyncio.run(main())
