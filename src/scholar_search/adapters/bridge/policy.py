"""Validation for messages crossing the native bridge.

The host is the second line of defence: even if the extension is compromised,
it can only ask for the nine verbs with the closed parameter schema. Domain
authority comes from the selected channel manifest (sent with the request),
not from a constant in the host.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from urllib.parse import urlparse

from ...core.params import validate_params

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

MAX_FRAME_BYTES = 2 * 1024 * 1024


def _host_allowed(host: str, domains: Iterable[str]) -> bool:
    host = host.casefold()
    for domain in domains:
        domain = domain.casefold()
        if host == domain or host.endswith("." + domain):
            return True
    return False


def validate_request(message: dict[str, Any], domains: Iterable[str] | None = None) -> str | None:
    """Return an error code, or None when the request is acceptable.

    ``domains=None`` means the caller relies on the kernel's manifest check;
    when domains are supplied they are enforced here as well.
    """

    action = message.get("action")
    if not isinstance(action, str) or action not in VERBS:
        return "policy.verb"

    params = message.get("params", {})
    error = validate_params(action, params)
    if error is not None:
        return error

    if action == "goto":
        parsed = urlparse(str(params["url"]))
        if parsed.scheme != "https":
            return "policy.url_scheme"
        if domains is not None and (
            not parsed.hostname or not _host_allowed(parsed.hostname, domains)
        ):
            return "policy.domain"
    return None
