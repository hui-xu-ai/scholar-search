"""Command line entry point.

P0 only wires the command surface. Implementations land in later phases.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from . import __version__
from .core import config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scholar-search",
        description="Read-only scholarly metadata retrieval (microkernel + channels).",
    )
    parser.add_argument("--version", action="version", version=f"scholar-search {__version__}")
    sub = parser.add_subparsers(dest="command")

    serve = sub.add_parser("serve", help="run the MCP server")
    serve.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)

    sub.add_parser("status", help="show session, quota and cooldown state")

    reset = sub.add_parser("reset", help="clear the risk cooldown after manual verification")
    reset.add_argument("--confirm", action="store_true", help="required to actually clear")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command is None:
        build_parser().print_help()
        return 0

    if args.command == "reset":
        if not args.confirm:
            print("refusing to clear the cooldown without --confirm", file=sys.stderr)
            return 2
        from .core.risk import RiskGuard

        RiskGuard().clear()
        print("risk cooldown cleared", file=sys.stderr)
        return 0

    config.ensure_home()

    if args.command == "status":
        from .bootstrap import build_service

        service = build_service()
        print(json.dumps(service.status(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "serve":
        from .bootstrap import build_service
        from .transports import http as http_transport
        from .transports import stdio as stdio_transport

        service = build_service()
        if args.transport == "http":
            http_transport.serve(service, host=args.host, port=args.port)
        else:
            stdio_transport.serve(service)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
