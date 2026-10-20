"""CNKI channel implementation, site version 2026.10."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ....core.contracts import (
    ChannelManifest,
    Plan,
    Record,
    SearchPage,
    SearchQuery,
)
from ....core.errors import ChannelError
from . import parse_detail, parse_search, plan_detail, plan_search


def _load_manifest() -> ChannelManifest:
    raw = json.loads((Path(__file__).parent.parent / "manifest.json").read_text("utf-8"))
    return ChannelManifest(
        channel=raw["channel"],
        site_version=raw["site_version"],
        schema_version=int(raw["schema_version"]),
        min_core=str(raw["min_core"]),
        domains=tuple(raw["domains"]),
        verbs=tuple(raw["verbs"]),
        capabilities=tuple(raw["capabilities"]),
        detail_url_prefixes=tuple(raw.get("detail_url_prefixes", ())),
    )


@dataclass
class CnkiChannel:
    manifest: ChannelManifest

    def plan_search(self, query: SearchQuery) -> Plan:
        return plan_search.build(query)

    def parse_search(self, html: str, *, query: SearchQuery) -> SearchPage:
        return parse_search.parse(html, query)

    def plan_detail(self, url: str) -> Plan:
        return plan_detail.build(url)

    def parse_detail(self, html: str, *, url: str) -> Record:
        return parse_detail.parse(html, url)

    def plan_journal(self, *, issn: str, year: int, issue: str) -> Plan:
        raise ChannelError("cnki channel does not implement journal listings yet")

    def parse_journal(
        self, html: str, *, issn: str, year: int, issue: str
    ) -> SearchPage:
        raise ChannelError("cnki channel does not implement journal listings yet")


def get_channel() -> CnkiChannel:
    manifest = _load_manifest()
    manifest.validate()
    return CnkiChannel(manifest=manifest)
