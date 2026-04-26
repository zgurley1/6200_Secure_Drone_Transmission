"""
MITM attack

Insecure Mode (Port 5005 -> 5005)
Drone blindly executes forged commands

Secure Mode (port 5006 -> 5006)
    - Modify: Drone rejects with "HMAC verification failed"
    - Replay: Drone rejects with "Replay/out-of-order detected"
    - Forward: attacker can read the ciphertext but not the plaintext


Usage:
    - Attacker binds on a fake port that the controller connects to
    - Attacker simultaneously connects to the real drone
    - Every intercepted message is presented to the attacker with options
        - [F] Forward - Pass the message through untouched
        - [M] Modify - Replace the command with an attacker-chosen one
        - [R] Replay - Re-send a previously captured message
    
        
    - Start order:
        1. drone.py (or drone_secure.py)
        2. attacker.py
        3. controller.py (or controller_secure.py)
"""

import socket
import json
import argparse
import threading

# Insecure: controller -> attacker(Listen: 5005) -> drone(5007)
# Secure: controller -> attacker(Listen:5006) -> drone(5008)

CONFIGS ={
    "insecure": {
        "listen_port": 5005,
        "drone_port": 5007,
        "label": "INSECURE"
    },
    "secure": {
        "listen_port": 5006,
        "drone_port": 5008,
        "label": "SECURE"
    }
}

HOST = '127.0.0.1'

MODIFY_MENU = """
    Available injection commands:
        1) LAND
        2) LIFTOFF
        3) MOVE x y z (ex. 999 999 999 for rogue coordinates)
        4) Custom JSON
"""

def choose_injected_command():
    print(MODIFY_MENU)
    choice = input("Attacker choice: ").strip()
    if choice == "1" or choice == "LAND":
        return {"action": "LAND"}
    elif choice == "2" or choice == "LIFTOFF":
        return {"action": "LIFTOFF"}
    elif choice == "3" or "MOVE" in choice:
        x = input("X: ").strip()
        y = input("Y: ").strip()
        z = input("Z: ").strip()
        return {"action": "MOVE", "x": x, "y": y, "z": z}
    elif choice == "4" or choice == "Custom JSON":
        custom = input("Enter JSON command: ").strip()
        try:
            return json.loads(custom)
        except json.JSONDecodeError:
            print("[Attacker] Invalid JSON. Forwarding original instead")
            return None
    else:
        print("[Attacker] Invalid choice. Forwarding original")
        return None
    
def display_intercepted(raw, mode, counter):
    print("\n" + "="*60)
    print(f"[Attacker] Intercepted message #{counter}")

    if mode == "insecure":
        try:
            cmd = json.loads(raw)
            print(f"Plaintext (visable): {json.dumps(cmd, indent=2)}")
        except Exception:
            print(f"Raw: {raw}")

    else:
        try:
            env = json.loads(raw)
            print(f"Encrypted envelop (cannot read plaintext)")
            print(f"IV: {env.get('iv','?')[:32]}...")
            print(f"CT: {env.get('ct','?')[:32]}...")
            print(f"Counter: {env.get('counter','?')}")
            print(f"HMAC: {env.get('hmac','?')[:32]}...")
        except Exception:
            print(f"Raw: {raw[:120]}")
    print("="*60)


def attack_prompt(raw, mode, captured_messages):
    print("\n Attack options:")
    print("[F] Forward  — pass through untouched")
    print("[M] Modify   — inject a forged command")
    if captured_messages:
        print(f"[R] Replay   — resend a captured message ({len(captured_messages)} available)")
    else:
        print("[R] Replay   — (no captured messages yet)")

    choice = input("\n  Attacker action> ").strip().upper()

    if choice == "F":
        print("[Attacker] Forwarding original message.")
        return raw.encode('utf-8')

    elif choice == "M":
        if mode == "insecure":
            injected = choose_injected_command()
            if injected is None:
                return raw.encode('utf-8')
            forged = json.dumps(injected)
            print(f"\n  [Attacker] *** INJECTING: {forged} ***")
            return (forged + "\n").encode('utf-8')
        else:
            # In secure mode: attacker can only tamper with the ciphertext bytes.
            # We flip a bit in the ciphertext to simulate a modification attempt.
            print("[Attacker] Cannot read plaintext. Attempting blind ciphertext tamper...")
            try:
                env = json.loads(raw)
                ct_bytes = bytearray(bytes.fromhex(env["ct"]))
                ct_bytes[0] ^= 0xFF           # flip bits in first byte
                env["ct"] = ct_bytes.hex()
                tampered = json.dumps(env)
                print("[Attacker] *** CIPHERTEXT TAMPERED — sending to drone ***")
                return (tampered + "\n").encode('utf-8')
            except Exception as e:
                print(f"[Attacker] Tamper failed: {e}. Forwarding original.")
                return raw.encode('utf-8')

    elif choice == "R":
        if not captured_messages:
            print("[Attacker] No captured messages yet. Forwarding original.")
            return raw.encode('utf-8')
        print("  Captured messages:")
        for i, msg in enumerate(captured_messages):
            if mode == "insecure":
                try:
                    preview = json.dumps(json.loads(msg))[:60]
                except Exception:
                    preview = msg[:60]
            else:
                try:
                    env = json.loads(msg)
                    preview = f"counter={env.get('counter','?')} ct={env.get('ct','?')[:20]}..."
                except Exception:
                    preview = msg[:60]
            print(f"[{i}] {preview}")
        idx = input("  Select index to replay> ").strip()
        try:
            replayed = captured_messages[int(idx)]
            print(f"[Attacker] *** REPLAYING message [{idx}] ***")
            return (replayed + "\n").encode('utf-8')
        except (IndexError, ValueError):
            print("[Attacker] Invalid index. Forwarding original.")
            return raw.encode('utf-8')

    else:
        print("[Attacker] Invalid choice. Forwarding original.")
        return raw.encode('utf-8')
    


def relay_responses(drone_sock, controller_conn, stop_event):
    # Forward drone responses back to the controller
    while not stop_event.is_set():
        try:
            drone_sock.settimeout(0.5)
            data = drone_sock.recv(4096)
            if not data:
                break
            response = data.decode('utf-8').strip()
            print(f"\n [Drone Response]: {response}")
            controller_conn.sendall(data)
        except socket.timeout:
            continue
        except Exception:
            break


def run(mode):
    cfg = CONFIGS[mode]
    listen_port = cfg["listen_port"]
    drone_port = cfg["drone_port"]
    label = cfg["label"]

    print(f"\n{'='*60}")
    print(f"MITM ATTACKER - {label} MODE")
    print(f"Listening for controller on port {listen_port}")
    print(f"Will forward to drone on port {drone_port}")
    print(f"\n{'='*60}")

    # Connect to real drone first
    print(f"[Attacker] Connecting to real dron on {HOST}:{drone_port}...")
    drone_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        drone_sock.connect((HOST, drone_port))
    except ConnectionRefusedError:
        print(f"[Attacker] ERROR: Could not reach drone on port {drone_port}")
        print(f"[Attacker] Make sure drone.py is running on port {drone_port}")
        return
    print(f"[Attacker] Conneted to real drone.\n")

    # Listen for the controller
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, listen_port))
        server.listen(1)
        print(f"[Attacker] Waiting for controller to connect on port {listen_port}... \n")

        controller_conn, addr = server.accept()
        print(f"[Attacker] Controller connected from {addr}")
        print(f"[Attacker] Now sitting in the middle")

        captured_messages = []
        msg_counter = 0
        stop_event = threading.Event()

        t = threading.Thread(target=relay_responses, args=(drone_sock, controller_conn, stop_event), daemon=True)

        t.start()

        with controller_conn:
            while True:
                try:
                    data = controller_conn.recv(4096)
                    if not data:
                        print("[Attacker] Controller disconnected")
                        break
                    raw = data.decode('utf-8').strip()
                    captured_messages.append(raw)
                    msg_counter += 1

                    display_intercepted(raw, mode, msg_counter)
                    to_send = attack_prompt(raw, mode, captured_messages[:-1])

                    drone_sock.sendall(to_send)
                except (ConnectionResetError, BrokenPipeError):
                    print("[Attacker] Connection lost")
                    break
                except KeyboardInterrupt:
                    print("\n [Attacker] Shutting down")
                    break
        stop_event.set()
        drone_sock.close()
        print("[Attacker] Session ended")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MITM Attacker Proxy")
    parser.add_argument("--mode", choices=["insecure", "secure"], required=True, help="Target the insecure (port 5005) or secure (port 5006) drone pair")
    args = parser.parse_args()
    run(args.mode)
