# -*- coding: utf-8 -*-
"""Store a user-entered database master passphrase.

The passphrase is written to resources/.master_key. A short passphrase is
stretched before it is stored. The file is not created until a passphrase is
supplied, and it must stay out of git.
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.crypto_engine import MASTER_KEY_PATH, save_master_passphrase


def create_master_key(passphrase: str, force: bool = False) -> Path:
    if MASTER_KEY_PATH.exists() and not force:
        raise FileExistsError(f"Master key already exists: {MASTER_KEY_PATH}")
    return save_master_passphrase(passphrase)


def main() -> int:
    parser = argparse.ArgumentParser(description="Store a user passphrase as resources/.master_key")
    parser.add_argument("--passphrase", required=True, help="Master passphrase entered by the user")
    parser.add_argument("--force", action="store_true", help="Replace an existing key file")
    args = parser.parse_args()
    try:
        path = create_master_key(args.passphrase, force=args.force)
    except FileExistsError as exc:
        print(exc)
        print("Refusing to rotate the key. Existing .db.enc files would become unreadable.")
        return 1
    print(f"Wrote master key to {path}")
    print("This file decrypts every .db.enc database. Keep it out of git and out of database backups.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
