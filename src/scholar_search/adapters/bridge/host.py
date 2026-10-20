"""Native messaging transport: framing and request correlation.

Framing matches the Chrome/Edge native messaging protocol: a 4-byte
little-endian length followed by a UTF-8 JSON object. stdout carries frames
only; every diagnostic goes to stderr.
"""

from __future__ import annotations

import json
import struct
import sys
import threading
import time
import uuid
from collections.abc import Callable
from typing import IO, Any

from .policy import MAX_FRAME_BYTES, validate_request


class BridgeClosed(RuntimeError):
    """The extension went away (stdin EOF) or the port was closed."""


def read_frame(stream: IO[bytes]) -> dict[str, Any] | None:
    header = stream.read(4)
    if not header:
        return None
    if len(header) < 4:
        raise BridgeClosed("truncated frame header")
    (length,) = struct.unpack("=I", header)
    if length == 0 or length > MAX_FRAME_BYTES:
        raise BridgeClosed(f"illegal frame length: {length}")
    payload = stream.read(length)
    if len(payload) < length:
        raise BridgeClosed("truncated frame body")
    message = json.loads(payload.decode("utf-8"))
    if not isinstance(message, dict):
        raise BridgeClosed("frame is not a JSON object")
    return message


def write_frame(stream: IO[bytes], message: dict[str, Any]) -> None:
    payload = json.dumps(message, ensure_ascii=False, allow_nan=False).encode("utf-8")
    stream.write(struct.pack("=I", len(payload)))
    stream.write(payload)
    stream.flush()


class BridgeHost:
    """Owns the extension connection and correlates requests with replies."""

    def __init__(
        self,
        stdin: IO[bytes] | None = None,
        stdout: IO[bytes] | None = None,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._in = stdin or sys.stdin.buffer
        self._out = stdout or sys.stdout.buffer
        self._clock = clock
        self._lock = threading.Condition()
        self._pending: dict[str, dict[str, Any] | None] = {}
        self._closed = False

    @property
    def closed(self) -> bool:
        with self._lock:
            return self._closed

    def serve_extension(self) -> None:
        """Read frames until EOF, dispatching replies to waiting callers."""

        try:
            while True:
                message = read_frame(self._in)
                if message is None:
                    break
                if message.get("type") == "action_result":
                    request_id = str(message.get("id", ""))
                    with self._lock:
                        if request_id in self._pending:
                            self._pending[request_id] = message
                            self._lock.notify_all()
        except (BridgeClosed, OSError, ValueError):
            pass
        finally:
            with self._lock:
                self._closed = True
                self._lock.notify_all()

    def request(
        self,
        action: str,
        params: dict[str, Any],
        *,
        timeout_s: float = 15.0,
        domains: tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        """Send one action to the extension and wait for its reply."""

        request_id = uuid.uuid4().hex
        message: dict[str, Any] = {
            "type": "action",
            "id": request_id,
            "action": action,
            "params": params,
        }
        error = validate_request(message, domains or ("kns.cnki.net", "www.cnki.net"))
        if error is not None:
            return {"ok": False, "error": error, "id": request_id}

        with self._lock:
            if self._closed:
                return {"ok": False, "error": "bridge.closed", "id": request_id}
            self._pending[request_id] = None

        try:
            write_frame(self._out, message)
        except OSError:
            with self._lock:
                self._pending.pop(request_id, None)
            return {"ok": False, "error": "bridge.write", "id": request_id}

        deadline = self._clock() + timeout_s
        with self._lock:
            while self._pending.get(request_id) is None and not self._closed:
                remaining = deadline - self._clock()
                if remaining <= 0:
                    break
                self._lock.wait(remaining)
            reply = self._pending.pop(request_id, None)

        if reply is None:
            return {
                "ok": False,
                "error": "bridge.timeout" if not self.closed else "bridge.closed",
                "id": request_id,
            }
        return reply
