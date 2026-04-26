import json
import socket
from config import PSK, pack_message

HOST = '127.0.0.1'
PORT = 5006


HELP_TEXT = """
----------------------------------------
    DRONE GOUND CONTROLLER - COMMANDS
----------------------------------------

liftoff - Take off (hover at z=10)
land - Land the drone
move <x> <y> <z> - Move to coordinates
status - Show current drone status
help - Display this menu
quit - Disconnect
"""

def parse_input(user_input):
    parts = user_input.strip().split()
    if not parts:
        return None
    
    action = parts[0].lower()

    if action == "liftoff":
        return {"action": "LIFTOFF"}
    
    elif action == "land":
        return {"action": "LAND"}
    
    elif action == "status":
        return {"action": "STATUS"}
    
    elif action == "move":
        if len(parts) != 4:
            print("[Controller] Usage: move <x> <y> <z>")
            return None
        try:
            return {"action": "MOVE", "x": float(parts[1]), "y": float(parts[2]), "z": float(parts[3])}
        except ValueError:
            print("[Controller] Coordinates must be numbers")
            return None
        
    else:
        print(f"[Controller] Unknown command: '{action}'. Type 'help' for options")
        return None
    
def run():
    print("[Controller Secure] Connecting to drone...")
    print(f"[Controller Secure] PSK loaded: {PSK.hex()[:16]}...  (first 8 bytes shown)")

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((HOST,PORT))
            print(f"[Controller Secure] Connected to drone at {HOST}:{PORT}")
            print("[Controller Secure] Security active: AES-CBC + HMAC-SHA256 + Counter\n")
            print(HELP_TEXT)

            counter = 0

            while True:
                try:
                    user_input = input("secure-controller> ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\n[Controller Secure] Disconnecting.")
                    break

                if not user_input:
                    continue
                if user_input.lower() == "help":
                    print(HELP_TEXT)
                    continue
                if user_input.lower() == "quit":
                    print("[Controller Secure] Disconnecting.")
                    break

                cmd = parse_input(user_input)
                if cmd is None:
                    continue

                # Encrypt + HMAC + stamp with counter
                payload = pack_message(cmd, counter, PSK)

                print(f"[Controller Secure] Plaintext : {json.dumps(cmd)}")
                print(f"[Controller Secure] Counter   : {counter}")
                print(f"[Controller Secure] Encrypted : {payload[:80]}...")

                sock.sendall((payload + "\n").encode('utf-8'))
                counter += 1  # increment after successful send

                response = sock.recv(4096).decode('utf-8').strip()
                print(f"[Controller Secure] Drone says: {response}\n")

    except ConnectionRefusedError:
        print(f"[Controller Secure] ERROR: Could not connect to drone at {HOST}:{PORT}.")
        print("[Controller Secure] Make sure drone_secure.py is running first.")

if __name__ == "__main__":
    run()