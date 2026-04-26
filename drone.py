import json
import socket
import argparse

HOST = '127.0.0.1'
PORT_DIRECT = 5005
PORT_MITM = 5007

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
    

def run(port):
    print(f"[Drone] Starting up. Listening on {HOST}:{port}...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind( (HOST,port) )
        server.listen(1)
        print("[DRONE] Waiting for controller connection...\n")

        conn, addr = server.accept()
        with conn:
            print(f"[DRONE] Controller connected from {addr}\n")
            while True:
                data = conn.recv(4096)
                if not data:
                    print("[DRONE] Controller disconnected.")
                    break
                raw = data.decode('utf-8').strip()
                print(f"[DRONE] Received: {raw}")

                try:
                    cmd = json.loads(raw)
                    response = handle_command(cmd)
                except json.JSONDecodeError:
                    response = "ERROR: Invalid command"

                print(f"[DRONE] Respone: {response}\n")
                conn.sendall((response + "\n").encode('utf-8'))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Drone Simulator (Insecure)")
    parser.add_argument(
        "--mitm",
        action="store_true",
        help=f"Run in MITM mode (port {PORT_MITM}) so the attacker proxy can sit in between"
    )
    args = parser.parse_args()
    port = PORT_MITM if args.mitm else PORT_DIRECT
    mode_label = "MITM mode" if args.mitm else "Direct mode"
    print(f"[Drone] {mode_label} — port {port}")
    run(port)