import json
import socket
from config import PSK, pack_message, unpack_message

HOST = '127.0.0.1'
PORT = 5006

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
    

def run():
    print(f"[Drone secure] Starting up. Listening on {HOST}:{PORT}...")
    print(f"[Drone Secure] PSK loaded: {PSK.hex()[:16]}...  (first 8 bytes shown)\n")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind( (HOST,PORT) )
        server.listen(1)
        print("[DRONE SECURE] Waiting for controller connection...\n")

        conn, addr = server.accept()
        with conn:
            print(f"[Drone Secure] Controller connected from {addr}")
            print("[Drone Secure] Security active: AES-CBC + HMAC-SHA256 + Counter\n")

            expected_counter = 0

            while True:
                data = conn.recv(4096)
                if not data:
                    print("[DRONE] Controller disconnected.")
                    break

                raw = data.decode('utf-8').strip()
                print(f"[Drone Secure] Received encrypted envelope (counter={expected_counter})")

                try:
                    cmd = unpack_message(raw, PSK, expected_counter)
                    print(f"[Drone Secure] Decrypted command: {cmd}")
                    expected_counter += 1  # advance only on success

                    response = handle_command(cmd)

                except ValueError as e:
                    # HMAC failure, replay, or bad padding — reject silently
                    print(f"[Drone Secure] SECURITY ALERT: {e}")
                    response = f"REJECTED: {e}"

                print(f"[Drone Secure] Response: {response}\n")
                conn.sendall((response + "\n").encode('utf-8'))

if __name__ == "__main__":
    run() 