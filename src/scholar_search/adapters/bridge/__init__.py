"""TCP client for the native host.

The host listens on loopback only and requires a per-run token. This adapter is
the kernel's view of the browser: one action in, one outcome out.
"""

from __future__ import annotations

import json
import socket
import uuid
from pathlib import Path
from typing import Any

from ...core.config import host_runtime_dir
from ...core.contracts import Action, ActionOutcome


class BridgeAdapter:
    name = "bridge"

    def __init__(
        self,
        endpoint: Path | None = None,
        *,
        timeout_s: float = 15.0,
    ) -> None:
        self._endpoint = endpoint or (host_runtime_dir() / "bridge.json")
        self._timeout = timeout_s
        self._socket: socket.socket | None = None
        self._reader: Any = None
        self._token: str | None = None
        self._port: int | None = None

    def _connect(self) -> None:
        if self._socket is not None:
            return
        raw = json.loads(self._endpoint.read_text(encoding="utf-8"))
        self._port = int(raw["port"])
        self._token = str(raw["token"])
        self._socket = socket.create_connection(("127.0.0.1", self._port), timeout=self._timeout)
        self._reader = self._socket.makefile("r", encoding="utf-8", newline="\n")

    def execute(self, action: Action, *, timeout_ms: int) -> ActionOutcome:
        try:
            self._connect()
            assert self._socket is not None and self._reader is not None
            request = {
                "id": uuid.uuid4().hex,
                "token": self._token,
                "action": action.verb,
                "params": dict(action.params),
                "timeout_ms": timeout_ms,
            }
            self._socket.sendall((json.dumps(request, ensure_ascii=False) + "\n").encode("utf-8"))
            line = self._reader.readline()
            if not line:
                raise ConnectionError("bridge closed the connection")
            reply = json.loads(line)
            return ActionOutcome(
                action=action,
                ok=bool(reply.get("ok")),
                data=dict(reply.get("data") or {}),
                error=reply.get("error"),
                duration_ms=int(reply.get("duration_ms") or 0),
                url=reply.get("url"),
            )
        except (OSError, ValueError, KeyError) as exc:
            return ActionOutcome(action=action, ok=False, error=f"bridge.error: {exc}")

    def close(self) -> None:
        for closable in (self._reader, self._socket):
            try:
                if closable is not None:
                    closable.close()
            except OSError:
                pass
        self._reader = None
        self._socket = None
