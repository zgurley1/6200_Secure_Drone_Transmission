import os
import hmac
import hashlib
import json
import struct
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


PSK = bytes.fromhex("4a7d1ed414474e4033ac29ccb8653d9ad53c6e50c7a6bb6d4e68e8f4df16ddf2")

# AES block size (bytes)
BLOCK_SIZE = 16

def pad(data: bytes) -> bytes:
    pad_len = BLOCK_SIZE - (len(data) % BLOCK_SIZE)
    return data + bytes([pad_len] * pad_len)

def unpad(data: bytes) -> bytes:
    pad_len = data[-1]
    if pad_len < 1 or pad_len > BLOCK_SIZE:
        raise ValueError("Invalid padding")
    if data[-pad_len:] != bytes([pad_len] * pad_len):
        raise ValueError("Padding mismatch")
    return data[:-pad_len]


# AES-CBC Encrypt / Decrypt
def aes_encrypt(plaintext: bytes, key: bytes) -> tuple[bytes, bytes]:
    """Returns (iv, ciphertext)."""
    iv = os.urandom(BLOCK_SIZE)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(pad(plaintext)) + encryptor.finalize()
    return iv, ciphertext

def aes_decrypt(iv: bytes, ciphertext: bytes, key: bytes) -> bytes:
    """Returns plaintext bytes."""
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    return unpad(padded)


# HMAC-SHA256
def compute_hmac(data: bytes, key: bytes) -> str:
    """Returns hex HMAC-SHA256 of data."""
    return hmac.new(key, data, hashlib.sha256).hexdigest()

def verify_hmac(data: bytes, key: bytes, expected: str) -> bool:
    """Constant-time HMAC comparison."""
    actual = compute_hmac(data, key)
    return hmac.compare_digest(actual, expected)


def pack_message(cmd: dict, counter: int, key: bytes) -> str:
    """Encrypt and authenticate a command dict. Returns JSON string."""
    plaintext = json.dumps(cmd).encode('utf-8')
    iv, ct = aes_encrypt(plaintext, key)

    # HMAC covers: iv || ciphertext || counter (8 bytes big-endian)
    mac_input = iv + ct + struct.pack(">Q", counter)
    mac = compute_hmac(mac_input, key)

    envelope = {
        "iv":      iv.hex(),
        "ct":      ct.hex(),
        "counter": counter,
        "hmac":    mac
    }
    return json.dumps(envelope)

def unpack_message(raw: str, key: bytes, expected_counter: int) -> dict:
    """
    Verify and decrypt a secure message.
    Raises ValueError if HMAC fails or counter is invalid.
    Returns the decrypted command dict.
    """
    envelope = json.loads(raw)
    iv      = bytes.fromhex(envelope["iv"])
    ct      = bytes.fromhex(envelope["ct"])
    counter = envelope["counter"]
    mac     = envelope["hmac"]

    # 1. Verify counter (replay protection)
    if counter != expected_counter:
        raise ValueError(f"Replay/out-of-order detected: expected {expected_counter}, got {counter}")

    # 2. Verify HMAC (integrity + authenticity)
    mac_input = iv + ct + struct.pack(">Q", counter)
    if not verify_hmac(mac_input, key, mac):
        raise ValueError("HMAC verification failed — message tampered or forged.")

    # 3. Decrypt
    plaintext = aes_decrypt(iv, ct, key)
    return json.loads(plaintext.decode('utf-8'))