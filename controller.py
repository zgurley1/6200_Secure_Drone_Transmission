import json
import socket

HOST = '127.0.0.1'
PORT = 5005


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
    print("[Controller] Connecting to drone...")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((HOST,PORT))
            print(f"[Controller] Connected to drone at {HOST}:{PORT}")
            print(HELP_TEXT)

            while True:
                try:
                    user_input = input("controller ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\n[Controller] Disconnecting")
                    break
                if not user_input:
                    continue

                if user_input.lower() == "help":
                    print(HELP_TEXT)
                    continue

                if user_input.lower() == "quit":
                    print("[Controller] Disconnecting")
                    break

                cmd = parse_input(user_input)
                if cmd is None:
                    continue

                payload = json.dumps(cmd)
                print(f"[Controller] Sending: {payload}")
                sock.sendall((payload + "\n").encode('utf-8'))

                response = sock.recv(4096).decode('utf-8').strip()
                print(f"[Controller] Drone Response: {response}\n")

    except ConnectionRefusedError:
        print(f"[Controller] ERROR: Could not connect to drone at {HOST}:{PORT}")
        print("[Controller] Make sure drone.py is running first")

if __name__ == "__main__":
    run()