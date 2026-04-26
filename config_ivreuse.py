import hmac
import hashlib
import json
import struct
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from config import PSK, pad, unpad, compute_hmac, verify_hmac
from config import aes_decrypt


FIXED_IV = bytes.fromhex("deadbeefcafebabe0102030405060708")  # never changes

def aes_encrypt_broken(plaintext: bytes, key: bytes) -> tuple[bytes, bytes]:
    cipher = Cipher(algorithms.AES(key), modes.CBC(FIXED_IV), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(pad(plaintext)) + encryptor.finalize()
    return FIXED_IV, ciphertext

def pack_message_broken(cmd: dict, counter: int, key: bytes) -> str:
    plaintext = json.dumps(cmd).encode('utf-8')
    iv, ct = aes_encrypt_broken(plaintext, key)

    mac_input = iv + ct + struct.pack(">Q", counter)
    mac = compute_hmac(mac_input, key)

    envelope = {
        "iv": iv.hex(),
        "ct": ct.hex(),
        "counter": counter,
        "hmac": mac
    }
    return json.dumps(envelope)

def unpack_message_broken(raw: str, key: bytes, expected_counter: int) -> dict:
    envelope = json.loads(raw)
    iv      = bytes.fromhex(envelope["iv"])
    ct      = bytes.fromhex(envelope["ct"])
    counter = envelope["counter"]
    mac     = envelope["hmac"]

    if counter != expected_counter:
        raise ValueError(f"Replay/out-of-order detected: expected {expected_counter}, got {counter}")

    mac_input = iv + ct + struct.pack(">Q", counter)
    if not verify_hmac(mac_input, key, mac):
        raise ValueError("HMAC verification failed — message tampered or forged.")


    
    plaintext = aes_decrypt(iv, ct, key)
    return json.loads(plaintext.decode('utf-8'))