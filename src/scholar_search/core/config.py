"""Configuration and hard limits.

Every value here is a floor or a ceiling, not a default. Channels and users
may make behaviour stricter, never looser. Loosening requires a new ADR.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

APP_NAME = "scholar-search"
ENV_HOME = "SCHOLAR_SEARCH_HOME"


@dataclass(frozen=True, slots=True)
class HardLimits:
    """Non-negotiable limits enforced by the kernel."""

    min_interval_ms: int = 3_000
    default_interval_ms: int = 4_000
    max_interval_ms: int = 6_000
    max_pages_per_call: int = 3
    max_pages_per_session: int = 8
    daily_request_limit: int = 200
    cooldown_hours: int = 24
    concurrency: int = 1
    max_actions_per_plan: int = 40
    max_plan_seconds: int = 120


HARD = HardLimits()


def app_home() -> Path:
    """Return the private runtime directory.

    Defaults to ``%LOCALAPPDATA%\\scholar-search`` on Windows and
    ``~/.local/share/scholar-search`` elsewhere. Never inside the repository.
    """

    override = os.environ.get(ENV_HOME)
    if override:
        return Path(override).expanduser().resolve()

    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / APP_NAME

    return Path.home() / ".local" / "share" / APP_NAME


def profiles_dir() -> Path:
    return app_home() / "profiles"


def cache_dir() -> Path:
    return app_home() / "cache"


def audit_dir() -> Path:
    return app_home() / "audit"


def logs_dir() -> Path:
    return app_home() / "logs"


def tmp_dir() -> Path:
    return app_home() / "tmp"


def ensure_home() -> Path:
    """Create the runtime tree and return its root."""

    root = app_home()
    for sub in (profiles_dir(), cache_dir(), audit_dir(), logs_dir(), tmp_dir()):
        sub.mkdir(parents=True, exist_ok=True)
    return root


def host_runtime_dir() -> Path:
    """Directory the browser-launched host may write to.

    It stays inside :func:`app_home` so the documented HOME boundary holds.
    The installer marks this subtree as low-integrity writable, because Chrome
    and Edge start native messaging hosts at low integrity.
    """

    return app_home() / "host"


def ensure_host_runtime() -> Path:
    root = host_runtime_dir()
    (root / "logs").mkdir(parents=True, exist_ok=True)
    return root
