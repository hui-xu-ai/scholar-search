"""Validation for messages crossing the native bridge.

The host is the second line of defence: even if the extension is compromised,
it can only ask for the nine verbs against allowlisted hosts.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from urllib.parse import urlparse

VERBS: frozenset[str] = frozenset(
    {
        "goto",
        "wait_for",
        "type",
        "click",
        "select",
        "read_html",
        "read_text",
        "scroll",
        "sleep",
    }
)

DEFAULT_DOMAINS: tuple[str, ...] = ("kns.cnki.net", "www.cnki.net")

MAX_FRAME_BYTES = 2 * 1024 * 1024
MAX_SLEEP_MS = 3_000


def _host_allowed(host: str, domains: Iterable[str]) -> bool:
    host = host.casefold()
    for domain in domains:
        domain = domain.casefold()
        if host == domain or host.endswith("." + domain):
            return True
    return False


def validate_request(
    message: dict[str, Any], domains: Iterable[str] = DEFAULT_DOMAINS
) -> str | None:
    """Return an error code, or None when the request is acceptable."""

    action = message.get("action")
    if not isinstance(action, str) or action not in VERBS:
        return "policy.verb"

    params = message.get("params", {})
    if not isinstance(params, dict):
        return "policy.params"

    if action == "goto":
        url = params.get("url")
        if not isinstance(url, str):
            return "policy.params"
        parsed = urlparse(url)
        if parsed.scheme != "https":
            return "policy.url_scheme"
        if not parsed.hostname or not _host_allowed(parsed.hostname, domains):
            return "policy.domain"
        return None

    if action in {"click", "read_text", "wait_for"}:
        selector = params.get("selector")
        if not isinstance(selector, str) or not selector.strip():
            return "policy.params"
        return None

    if action == "type":
        if not isinstance(params.get("selector"), str) or not params["selector"].strip():
            return "policy.params"
        text = params.get("text")
        if not isinstance(text, str) or len(text) > 500:
            return "policy.params"
        return None

    if action == "select":
        if not isinstance(params.get("selector"), str) or not isinstance(
            params.get("value"), str
        ):
            return "policy.params"
        return None

    if action == "scroll":
        if params.get("to") not in {"top", "bottom"}:
            return "policy.params"
        return None

    if action == "sleep":
        ms = params.get("ms")
        if not isinstance(ms, int) or isinstance(ms, bool) or not 0 <= ms <= MAX_SLEEP_MS:
            return "policy.params"
        return None

    return None
