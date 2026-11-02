"""Runtime paths shared by source checkouts and installed KAIRIS commands."""

from __future__ import annotations

import os
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def workspace_root() -> Path:
    """Return the writable KAIRIS workspace without assuming site-packages is writable."""
    configured = os.getenv("KAIRIS_WORKSPACE")
    if configured:
        return Path(configured).expanduser().resolve()
    if (PACKAGE_ROOT / "scripts").is_dir() and (PACKAGE_ROOT / "config").is_dir():
        return PACKAGE_ROOT
    return Path.cwd().resolve()


def default_config_path() -> Path:
    """Prefer a workspace config and otherwise use the packaged protocol defaults."""
    workspace_config = workspace_root() / "config" / "protocol_config.json"
    if workspace_config.is_file():
        return workspace_config
    return PACKAGE_ROOT / "config" / "protocol_config.json"


def local_config_path() -> Path:
    """Return the writable, unversioned per-installation configuration path."""
    return workspace_root() / "config" / "local_config.json"
