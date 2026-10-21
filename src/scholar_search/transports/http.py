"""Loopback HTTP transport with a per-install bearer token.

The port is reachable by every local process, and a browser page can attempt
DNS rebinding, so requests must carry a token and a loopback Host header.
"""

from __future__ import annotations

import secrets
from typing import Any

import uvicorn
from starlette.types import ASGIApp, Receive, Scope, Send

from ..core.config import app_home
from ..core.service import ScholarService
from ..server import build_server

TOKEN_NAME = "http-token"


def load_token() -> str:
    path = app_home() / TOKEN_NAME
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    token = secrets.token_urlsafe(32)
    path.write_text(token, encoding="utf-8")
    return token


LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def _hostname(header: str) -> str:
    value = header.strip()
    if value.startswith("["):
        end = value.find("]")
        return value[1:end] if end > 0 else ""
    if value.count(":") == 1:
        return value.split(":", 1)[0]
    return value


class TokenMiddleware:
    def __init__(self, app: ASGIApp, token: str) -> None:
        self.app = app
        self.token = token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {key.decode().lower(): value.decode() for key, value in scope["headers"]}
        if _hostname(headers.get("host", "")).casefold() not in LOOPBACK_HOSTS:
            await self._deny(send, 403)
            return

        authorization = headers.get("authorization", "")
        if not secrets.compare_digest(authorization, f"Bearer {self.token}"):
            await self._deny(send, 401)
            return

        await self.app(scope, receive, send)

    @staticmethod
    async def _deny(send: Send, status: int) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": b'{"error":"unauthorized"}'})


def serve(service: ScholarService, host: str = "127.0.0.1", port: int = 8765) -> None:
    server = build_server(service)
    server.settings.host = host
    server.settings.port = port
    app: Any = server.streamable_http_app()
    app.add_middleware(TokenMiddleware, token=load_token())
    uvicorn.run(app, host=host, port=port, log_level="warning")


__all__ = ["TokenMiddleware", "load_token", "serve"]
