# -*- coding: utf-8 -*-
"""Create the local database master key.

The key is a random UTF-8 secret stored in resources/.master_key.
It is not written into app_config.toml and must stay out of git.
"""

import argparse
import os
import secrets
import stat
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.crypto_engine import MASTER_KEY_PATH, MIN_MASTER_KEY_BYTES


def _restrict_to_current_user(path: Path) -> None:
    if sys.platform == "win32":
        username = os.environ.get("USERNAME")
        if not username:
            return
        subprocess.run(
            ["icacls", str(path), "/inheritance:r", "/grant:r", f"{username}:(R,W)"],
            check=False,
            capture_output=True,
            text=True,
        )
        return
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def create_master_key(force: bool = False) -> Path:
    if MASTER_KEY_PATH.exists() and not force:
        raise FileExistsError(f"Master key already exists: {MASTER_KEY_PATH}")
    MASTER_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    secret = secrets.token_urlsafe(MIN_MASTER_KEY_BYTES)
    MASTER_KEY_PATH.write_text(secret + "\n", encoding="utf-8")
    _restrict_to_current_user(MASTER_KEY_PATH)
    return MASTER_KEY_PATH


def main() -> int:
    parser = argparse.ArgumentParser(description="Create resources/.master_key")
    parser.add_argument("--force", action="store_true", help="Replace an existing key file")
    args = parser.parse_args()
    try:
        path = create_master_key(force=args.force)
    except FileExistsError as exc:
        print(exc)
        print("Refusing to rotate the key. Existing .db.enc files would become unreadable.")
        return 1
    print(f"Wrote master key to {path}")
    print("This file decrypts every .db.enc database. Keep it out of git and out of database backups.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
