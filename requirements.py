import sys
import subprocess

REQUIRED_PYTHON = (3,10)
PACKAGES = [
    "cryptography",
]

def check_python_version():
    major, minor = sys.version_info[:2]
    if (major, minor) < REQUIRED_PYTHON:
        print(f"[!] Python {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}+ is required.")
        print(f"You are running Python {major}.{minor}.")
        print(f"Please upgrade at https://www.python.org/downloads/")
        sys.exit(1)
    print(f"Python {major}.{minor} detected — OK")

def install_packages():
    print(f"\n[*] Checking {len(PACKAGES)} required package(s)...\n")
    all_ok = True
    for package in PACKAGES:
        # Check if already importable before attempting install
        import_name = package.split("[")[0].replace("-", "_")
        try:
            __import__(import_name)
            print(f"{package} already installed — skipping.\n")
            continue
        except ImportError:
            pass

        print(f"Installing: {package}")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"{package} installed successfully.\n")
        else:
            # Retry with --break-system-packages for Linux system-managed envs
            result2 = subprocess.run(
                [sys.executable, "-m", "pip", "install", package, "--break-system-packages"],
                capture_output=True,
                text=True
            )
            if result2.returncode == 0:
                print(f"{package} installed successfully (system env).\n")
            else:
                print(f"Failed to install {package}.")
                print(f"Try manually: pip install {package}")
                all_ok = False
    return all_ok

def verify_imports():
    print("[*] Verifying imports...\n")
    all_ok = True
    checks = [
        ("cryptography.hazmat.primitives.ciphers", "AES-CBC encryption"),
        ("hmac",                                   "HMAC-SHA256 authentication"),
        ("hashlib",                                "SHA256 hashing"),
        ("socket",                                 "TCP socket communication"),
        ("json",                                   "Command serialization"),
        ("argparse",                               "CLI argument parsing"),
    ]
    for module, description in checks:
        try:
            __import__(module)
            print(f"{module:45s} — {description}")
        except ImportError:
            print(f"{module:45s} — MISSING ({description})")
            all_ok = False
    return all_ok



if __name__ == "__main__":
    print("=" * 60)
    print("Secure Drone Transmission — Dependency Setup")
    print("ITIS 6200 Course Project")
    print("=" * 60 + "\n")

    check_python_version()

    ok = install_packages()
    if not ok:
        print("Some packages failed to install. Try running manually:")
        for p in PACKAGES:
            print(f"pip install {p}")
        sys.exit(1)

    ok = verify_imports()
    if not ok:
        print("\nSome imports failed. Please check the errors above.")
        sys.exit(1)
