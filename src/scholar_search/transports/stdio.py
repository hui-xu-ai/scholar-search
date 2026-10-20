"""stdio transport."""

from __future__ import annotations

from ..core.service import ScholarService
from ..server import build_server


def serve(service: ScholarService) -> None:
    build_server(service).run(transport="stdio")


__all__ = ["serve"]
