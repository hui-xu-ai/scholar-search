"""Error hierarchy.

Errors carry enough structure for transports to render actionable messages
without leaking page content or session material.
"""

from __future__ import annotations

from dataclasses import dataclass


class ScholarSearchError(Exception):
    """Base class for all project errors."""


class ConfigurationError(ScholarSearchError):
    """Invalid or unsafe configuration."""


class ChannelError(ScholarSearchError):
    """Channel could not be loaded or is not compatible."""


class ChannelNotFound(ChannelError):
    """No channel registered under that name."""


class PolicyError(ScholarSearchError):
    """An action, domain, or rate violates the policy."""

    def __init__(self, message: str, *, rule: str = "") -> None:
        super().__init__(message)
        self.rule = rule


class RiskBlocked(ScholarSearchError):
    """A risk signal was detected; execution stops immediately."""

    def __init__(self, message: str, *, signal: str, cooldown_until: str) -> None:
        super().__init__(message)
        self.signal = signal
        self.cooldown_until = cooldown_until

    def to_payload(self) -> dict[str, str]:
        return {
            "status": "blocked",
            "signal": self.signal,
            "cooldown_until": self.cooldown_until,
            "action_required": "manual_verification",
        }


class ParseError(ScholarSearchError):
    """Page structure did not match the channel's expectations."""

    @dataclass(frozen=True, slots=True)
    class Context:
        channel: str
        site_version: str
        purpose: str

    def __init__(self, message: str, *, context: Context | None = None) -> None:
        super().__init__(message)
        self.context = context


class BridgeError(ScholarSearchError):
    """Native messaging transport failed."""


class BridgeTimeout(BridgeError):
    """The browser did not answer within the deadline."""


class SmokeTestFailed(ScholarSearchError):
    """A transport or channel self-check failed."""
