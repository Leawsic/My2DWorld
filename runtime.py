"""Centralized paths and one-time migration for runtime-generated data."""

import os
import shutil

RUN_DIR = "run"
ACCOUNTS_DIR = os.path.join(RUN_DIR, "accounts")
CONFIG_DIR = os.path.join(RUN_DIR, "config")
LOGS_DIR = os.path.join(RUN_DIR, "logs")
WORLDS_DIR = os.path.join(RUN_DIR, "worlds")

_migrated = False


def _copy_legacy_directory(source, destination):
    """Copy legacy data only when the new runtime location does not exist."""
    if os.path.isdir(source) and not os.path.exists(destination):
        shutil.copytree(source, destination)


def _copy_legacy_file(source, destination):
    """Copy a legacy file only when no runtime replacement exists yet."""
    if os.path.isfile(source) and not os.path.exists(destination):
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        shutil.copy2(source, destination)


def ensure_runtime_data():
    """Create ``run/`` and preserve existing generated data on first use."""
    global _migrated
    if _migrated:
        return

    _copy_legacy_directory("Account_and_password", ACCOUNTS_DIR)
    _copy_legacy_directory("logs", LOGS_DIR)
    _copy_legacy_directory("worlds", WORLDS_DIR)
    _copy_legacy_file("config/basic.json", os.path.join(CONFIG_DIR, "basic.json"))

    for directory in (ACCOUNTS_DIR, CONFIG_DIR, LOGS_DIR, WORLDS_DIR):
        os.makedirs(directory, exist_ok=True)
    _migrated = True
