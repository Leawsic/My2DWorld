"""
Logging system for My2DWorld.
Logs user login/registration and game events to logs/ directory.
Passwords are never stored in plain text - only SHA-256 hash + salt.
Log file is named with the system time: logs/YYYY-MM-DD_HH-MM-SS.log
"""

import os
from datetime import datetime

LOGS_DIR = "logs"


def _ensure_dir():
    """Ensure the logs directory exists."""
    os.makedirs(LOGS_DIR, exist_ok=True)


# Global log file path, set by init_log()
_log_path = None


def init_log():
    """
    Initialize the log file using the current system time.
    Creates logs/YYYY-MM-DD_HH-MM-SS.log and writes a header.
    Returns the log file path, or None on failure.
    """
    global _log_path
    _ensure_dir()
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        _log_path = os.path.join(LOGS_DIR, f"{timestamp}.log")
        with open(_log_path, "a", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write(f"My2DWorld Log - Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n")
        return _log_path
    except Exception as e:
        print(f"Warning: failed to init log file: {e}")
        _log_path = None
        return None


def log_event(message: str):
    """
    Write a timestamped message to the current log file.
    Creates the log file automatically if not yet initialized.
    """
    global _log_path
    if _log_path is None:
        init_log()
    if _log_path is None:
        return
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(_log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        print(f"Warning: failed to write log: {e}")


def log_login(username: str, password_hash: str, salt: str, success: bool):
    """
    Log a login attempt.
    Only the SHA-256 hash + salt are written - the plaintext password is never stored.
    """
    result = "SUCCESS" if success else "FAILED"
    log_event(f"Login {result}: user={username} password_hash={password_hash} salt={salt}")


def log_register(username: str, password_hash: str, salt: str, success: bool):
    """
    Log a registration attempt.
    Only the SHA-256 hash + salt are written - the plaintext password is never stored.
    """
    result = "SUCCESS" if success else "FAILED"
    log_event(f"Register {result}: user={username} password_hash={password_hash} salt={salt}")


def log_game_start(username: str):
    """Log the start of a game session."""
    log_event(f"Game Start: user={username}")


def log_game_end(username: str, reason: str):
    """
    Log the end of a game session.
    reason: e.g. 'quit' (exit to desktop) or 'homepage' (back to main menu).
    """
    log_event(f"Game End: user={username} reason={reason}")


def log_pause(username: str):
    """Log when the game is paused."""
    log_event(f"Game Paused: user={username}")


def log_resume(username: str):
    """Log when the game is resumed."""
    log_event(f"Game Resumed: user={username}")