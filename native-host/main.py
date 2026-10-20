"""Native messaging host entry point.

Started by Edge/Chrome through a registry-registered manifest. It speaks the
native messaging protocol on stdin/stdout and a line-delimited JSON protocol
on a loopback TCP port for the MCP server.

stdout must carry protocol frames only; every diagnostic goes to stderr.
"""

from __future__ import annotations

import contextlib
import json
import os
import secrets
import socket
import sys
import threading
import time
from pathlib import Path

from scholar_search.adapters.bridge.host import BridgeHost
from scholar_search.adapters.bridge.policy import DEFAULT_DOMAINS
from scholar_search.core.config import ensure_host_runtime, host_runtime_dir

HOST_NAME = "com.scholar.search"
ENDPOINT_NAME = "bridge.json"


def write_endpoint(port: int, token: str) -> Path:
    path = host_runtime_dir() / ENDPOINT_NAME
    payload = {"port": port, "token": token, "pid": os.getpid(), "started": time.time()}
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def clear_endpoint(path: Path) -> None:
    with contextlib.suppress(OSError):
        path.unlink()


def serve_client(
    connection: socket.socket, host: BridgeHost, token: str, domains: tuple[str, ...]
) -> None:
    reader = connection.makefile("r", encoding="utf-8", newline="\n")
    try:
        for line in reader:
            if not line.strip():
                continue
            try:
                request = json.loads(line)
            except ValueError:
                connection.sendall(b'{"ok":false,"error":"protocol.json"}\n')
                continue

            if not secrets.compare_digest(str(request.get("token", "")), token):
                connection.sendall(b'{"ok":false,"error":"policy.token"}\n')
                continue

            action = request.get("action")
            params = request.get("params") or {}
            timeout_ms = int(request.get("timeout_ms") or 15_000)
            if not isinstance(action, str) or not isinstance(params, dict):
                connection.sendall(b'{"ok":false,"error":"policy.params"}\n')
                continue

            reply = host.request(
                action,
                params,
                timeout_s=timeout_ms / 1000,
                domains=domains,
            )
            connection.sendall(
                (json.dumps(reply, ensure_ascii=False) + "\n").encode("utf-8")
            )
    except OSError:
        pass
    finally:
        try:
            reader.close()
            connection.close()
        except OSError:
            pass


def start_tcp_server(
    host: BridgeHost, token: str, domains: tuple[str, ...]
) -> tuple[socket.socket, int]:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(4)
    port = int(server.getsockname()[1])

    def accept_loop() -> None:
        while True:
            try:
                connection, _ = server.accept()
            except OSError:
                return
            threading.Thread(
                target=serve_client,
                args=(connection, host, token, domains),
                daemon=True,
            ).start()

    threading.Thread(target=accept_loop, daemon=True, name="tcp-accept").start()
    return server, port


def _log(message: str) -> None:
    """Diagnostics go to a file because Chrome discards host stderr."""
    try:
        path = host_runtime_dir() / "logs" / "host.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")
    except OSError:
        pass


def host_already_running() -> bool:
    """Return True when another host still answers on the recorded port."""

    path = host_runtime_dir() / ENDPOINT_NAME
    try:
        info = json.loads(path.read_text(encoding="utf-8"))
        port = int(info["port"])
    except (OSError, ValueError, KeyError, TypeError):
        return False
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def main() -> int:
    try:
        ensure_host_runtime()
        if host_already_running():
            _log(f"another host is alive; exiting pid={os.getpid()}")
            return 0
        _log(f"start pid={os.getpid()} cwd={os.getcwd()}")
        host = BridgeHost()
        token = secrets.token_urlsafe(24)
        domains = tuple(os.environ.get("SCHOLAR_SEARCH_DOMAINS", "").split(",")) or DEFAULT_DOMAINS
        domains = tuple(domain for domain in domains if domain)

        server, port = start_tcp_server(host, token, domains)
        endpoint = write_endpoint(port, token)
        _log(f"ready port={port} endpoint={endpoint}")
        print(
            f"scholar-search host ready: 127.0.0.1:{port} ({endpoint})",
            file=sys.stderr,
            flush=True,
        )

        try:
            host.serve_extension()
        finally:
            _log("extension channel closed; shutting down")
            clear_endpoint(endpoint)
            server.close()
        return 0
    except BaseException as error:
        import traceback

        _log("fatal: " + "".join(traceback.format_exception(error)))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
