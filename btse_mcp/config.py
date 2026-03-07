"""
Account configuration with Fernet-encrypted storage.

Files
-----
~/.config/btse-mcp/key          Fernet key (chmod 600 on Unix, created on first use)
~/.config/btse-mcp/accounts.enc Encrypted JSON blob of all accounts

Account record
--------------
{
    "account_id": {
        "api_key":    "...",
        "api_secret": "...",
        "testnet":    true | false
    },
    ...
}
"""

import json
import platform
import sys
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet

CONFIG_DIR    = Path.home() / ".config" / "btse-mcp"
KEY_FILE      = CONFIG_DIR / "key"
ACCOUNTS_FILE = CONFIG_DIR / "accounts.enc"


def _ensure_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _set_file_permissions(path: Path) -> None:
    """
    FIX: chmod(0o600) is a no-op on Windows — warn the user instead.
    On Unix this restricts the file to owner read/write only.
    """
    if platform.system() == "Windows":
        # Windows does not support Unix-style permissions.
        # The file is as secure as the user's home directory allows.
        # For stronger protection consider using Windows DPAPI (win32crypt).
        print(
            f"  Warning: on Windows, {path.name} is not locked to your user only.\n"
            f"  Ensure your home directory ({Path.home()}) is not shared.",
            file=sys.stderr,
        )
    else:
        path.chmod(0o600)


def _load_or_create_fernet() -> Fernet:
    _ensure_dir()
    if KEY_FILE.exists():
        key = KEY_FILE.read_bytes()
    else:
        key = Fernet.generate_key()
        KEY_FILE.write_bytes(key)
        _set_file_permissions(KEY_FILE)
    return Fernet(key)


def _load_raw() -> dict:
    """Return the decrypted accounts dict, or {} if no file yet."""
    if not ACCOUNTS_FILE.exists():
        return {}
    f = _load_or_create_fernet()
    return json.loads(f.decrypt(ACCOUNTS_FILE.read_bytes()))


def _save_raw(accounts: dict) -> None:
    f         = _load_or_create_fernet()
    encrypted = f.encrypt(json.dumps(accounts).encode())
    ACCOUNTS_FILE.write_bytes(encrypted)
    _set_file_permissions(ACCOUNTS_FILE)


def save_account(
    account_id: str,
    api_key: str,
    api_secret: str,
    testnet: bool = False,
) -> None:
    accounts = _load_raw()
    accounts[account_id] = {
        "api_key":    api_key,
        "api_secret": api_secret,
        "testnet":    testnet,
    }
    _save_raw(accounts)
    print(f"Account '{account_id}' saved to {ACCOUNTS_FILE}")


def load_account(account_id: str) -> Optional[dict]:
    """Return account dict or None if not found."""
    return _load_raw().get(account_id)


def list_accounts() -> list[dict]:
    """Return list of dicts with id and testnet flag for display."""
    return [
        {"id": k, "testnet": v.get("testnet", False)}
        for k, v in _load_raw().items()
    ]


def delete_account(account_id: str) -> None:
    accounts = _load_raw()
    if account_id in accounts:
        del accounts[account_id]
        _save_raw(accounts)
        print(f"Account '{account_id}' deleted.")
    else:
        print(f"Account '{account_id}' not found.")
