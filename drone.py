import socket
import json

HOST = '127.0.0.1'
PORT = 5005

state = {
    "status": "grounded",
    "x": 0.0,
    "y": 0.0,
    "z": 0.0,
}

def print_state():
    print(f"\n [Drone Status]")
    print(f"    Status: {state['status']}")
    print(f"    Position (x,y,z): ({state['x'], state['y'], state['z']})")
    print()

def handle_command(cmd):
    action = cmd.get("action", "").upper()

    if action == "LIFTOFF":
        if state["status"] == "airborne":
            return "WARNING: Aircraft already airborne. Command ignored."
        state["status"] = "airborne"
        state["z"] = 10.0
        print_state()
        return f"OK: Drone lift off successful. Hovering at {state['z']}"

    elif action == "LAND":
        if state["status"] == "grounded":
            return "WARNING: Aircraft already grounded. Command ignored."
        state["status"] = "grounded"
        state["x"] = 0.0
        state["y"] = 0.0
        state["z"] = 0.0
        print_state()
        return "OK: Drone landed."

    elif action == "MOVE":
        if state["status"] == "grounded":
            return "WARNING: Cannot move while grounded. Please liftoff first"
        state["x"] = cmd.get("x", state["x"])
        state["y"] = cmd.get("y", state["y"])
        state["z"] = cmd.get("z", state["z"])
        print_state()
        return f"OK: Moved to ({state['x']}, {state['y']}, {state['z']})"

    elif action == "STATUS":
        print_state()
        return json.dumps(state)
    else:
        return f"ERROR: Unknown command '{action}'"