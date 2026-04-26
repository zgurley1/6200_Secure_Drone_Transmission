"""
Simulates a passive eavesdropper who has captured cyphertext from an AES-CBC session where the same IV is used for each message

Modes:
    - Simulate: Self contained demo
    - Live: Transparent proxy on port 5009, collect live ciphertexts
"""

import json
import argparse
import socket
import threading
from config import PSK, pad
from config_ivreuse import aes_encrypt_broken, FIXED_IV

HOST = '127.0.0.1'
SNIFF_PORT = 5009

def xor_bytes(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))

def run_simulate():
    print("\n" + "="*65)
    print("  IV REUSE ATTACK — AES-CBC CIPHERTEXT FINGERPRINTING")
    print("  Attacker is a passive eavesdropper with no knowledge of the key.")
    print("="*65)

    # Simulate a realistic drone session: some commands repeated
    session_commands = [
        {"action": "LIFTOFF"},
        {"action": "MOVE", "x": 10.0, "y": 20.0, "z": 30.0},
        {"action": "MOVE", "x": 50.0, "y": 75.0, "z": 30.0},
        {"action": "LIFTOFF"},   # repeated — operator hit it twice
        {"action": "STATUS"},
        {"action": "LAND"},
        {"action": "LIFTOFF"},   # repeated again
        {"action": "LAND"},      # repeated
    ]

    print(f"\n  [Session] Controller sends {len(session_commands)} commands.")
    print(f"  [Attacker] Captures all ciphertexts off the wire.\n")

    captured = []
    for i, cmd in enumerate(session_commands):
        _, ct = aes_encrypt_broken(json.dumps(cmd).encode('utf-8'), PSK)
        captured.append((i + 1, ct, cmd))
        print(f"Msg {i+1:02d}  CT[0:8]= {ct[:8].hex()}...  (attacker sees this, NOT the plaintext)")

    print(f"\n[Step 1] Attacker checks whether any IVs repeat.")
    print(f"IV in every envelope : {FIXED_IV.hex()}")
    print(f"!! ALL {len(captured)} messages share the same IV !!")

    print(f"\n[Step 2] Attacker groups messages by identical ciphertext.")
    print(f"Equal ciphertext  =>  Equal plaintext  (same command was sent)")

    groups: dict[bytes, list[int]] = {}
    for msg_num, ct, _ in captured:
        key = ct[:16]  # compare first block
        groups.setdefault(key, []).append(msg_num)

    fingerprint_map: dict[bytes, str] = {}
    for ct_key, msg_nums in groups.items():
        if len(msg_nums) > 1:
            print(f"\n !! Messages {msg_nums} have IDENTICAL ciphertext block 0: {ct_key.hex()}")
            print(f"Attacker knows these are the same command.")

    print(f"\n[Step 3] Attacker builds a ciphertext dictionary.")
    print(f"By observing drone behavior (GPS telemetry, RF emissions)")
    print(f"the attacker correlates ciphertexts to known actions:\n")

    fingerprint_map: dict[bytes, str] = {}
    for ct_key, msg_nums in groups.items():
        if len(msg_nums) > 1:
            actual_action = next(
                cmd["action"] for _, ct, cmd in captured
                if ct[:16] == ct_key
            )
            fingerprint_map[ct_key] = actual_action

    print(f"Ciphertext dict (attacker's learned map):")
    for ct_key, label in fingerprint_map.items():
        print(f"    {ct_key.hex()} → {label}")

    print(f"\n[Step 4] Attacker decodes the full session without the key:\n")
    correct = 0
    for msg_num, ct, actual_cmd in captured:
        ct_block = ct[:16]
        guessed = fingerprint_map.get(ct_block, "UNKNOWN (not yet learned)")
        actual  = actual_cmd["action"]
        hit     = guessed == actual
        if hit:
            correct += 1
        marker = "1" if hit else "0"
        print(f"{marker} Msg {msg_num:02d}: attacker guesses [{guessed:30s}]  actual: {actual}")

    pct = correct * 100 // len(captured)
    print(f"\n[Result] Attacker correctly identified {correct}/{len(captured)} "
          f"commands ({pct}%) - with ZERO cryptanalysis.")
    print(f"Every additional session improves the dictionary further.")

    print(f"\n[Why HMAC doesn't help here]")
    print(f"HMAC verifies authenticity - it cannot hide ciphertext patterns.")
    print(f"The drone accepts every message. No alerts are raised.")
    print(f"The flaw is structural: it leaks information before decryption.")

    print(f"\n[Summary]")
    print(f"Fixed IV => identical commands produce identical ciphertexts.")
    print(f"Passive attacker builds a command dictionary in one session.")
    print(f"No key recovery needed - ciphertext comparison is enough.")
    print(f"HMAC is unaffected - drone sees no errors whatsoever.")
    print(f"Fix: one line - replace FIXED_IV with os.urandom(16) per message.")
    print("="*65 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IV Reuse Attack Demonstrator")
    parser.add_argument("--simulate", action="store_true",
                        help="Self-contained simulation (no drone/controller needed)")
    args = parser.parse_args()

    if args.simulate:
        run_simulate()
    else:
        print("Usage: python iv_analysis.py --simulate")
        print("       python iv_analysis.py --live")