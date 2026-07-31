"""
Account management system with SHA-256 password hashing.
Accounts stored as JSON files in Account_and_password/ directory.
"""

import hashlib
import json
import os
import secrets

from logger import log_login, log_register

ACCOUNT_DIR = "Account_and_password"
DEFAULT_USERNAME = "steve"
DEFAULT_PASSWORD = "1234asdf"


def _ensure_dir():
    """Ensure the account directory exists."""
    os.makedirs(ACCOUNT_DIR, exist_ok=True)


def _account_path(username: str) -> str:
    """Get the file path for a given username."""
    return os.path.join(ACCOUNT_DIR, f"{username}.json")


def hash_password(password: str, salt: str | None = None) -> tuple:
    """
    Hash a password with SHA-256 + salt.
    Returns (hash_hex, salt_hex).
    """
    if salt is None:
        salt = secrets.token_hex(16)
    salted = salt + password
    h = hashlib.sha256(salted.encode("utf-8")).hexdigest()
    return h, salt


def register(username: str, password: str) -> bool:
    """
    Register a new user. Returns True if successful, False if already exists.
    """
    _ensure_dir()
    path = _account_path(username)
    if os.path.exists(path):
        pwd_hash, salt = hash_password(password)
        log_register(username, pwd_hash, salt, False)
        return False  # User already exists

    pwd_hash, salt = hash_password(password)
    data = {
        "username": username,
        "password_hash": pwd_hash,
        "salt": salt
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    log_register(username, pwd_hash, salt, True)
    return True


def login(username: str, password: str) -> bool:
    """
    Verify login credentials. Returns True if valid.
    """
    _ensure_dir()
    path = _account_path(username)
    if not os.path.exists(path):
        pwd_hash, salt = hash_password(password)
        log_login(username, pwd_hash, salt, False)
        return False

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    stored_hash = data.get("password_hash", "")
    salt = data.get("salt", "")
    computed_hash, _ = hash_password(password, salt)
    success = computed_hash == stored_hash
    log_login(username, stored_hash, salt, success)
    return success


def user_exists(username: str) -> bool:
    """Check if a user account exists."""
    return os.path.exists(_account_path(username))


def init_default_account():
    """Create the default 'steve' account if it doesn't exist."""
    if not user_exists(DEFAULT_USERNAME):
        register(DEFAULT_USERNAME, DEFAULT_PASSWORD)
        print(f"  Created default account: {DEFAULT_USERNAME}")
        return True
    return False