"""Shared test doubles."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from scholar_search.core.contracts import (
    Action,
    ChannelManifest,
    Plan,
    Record,
    SearchPage,
    SearchQuery,
)
from scholar_search.core.registry import ChannelSpec


def make_manifest(**overrides: object) -> ChannelManifest:
    data: dict[str, object] = {
        "channel": "fake",
        "site_version": "2026.10",
        "schema_version": 1,
        "min_core": "0.1.0",
        "domains": ("example.org",),
        "verbs": ("goto", "wait_for", "click", "read_html"),
        "capabilities": ("search", "detail"),
        "detail_url_prefixes": ("/article/",),
    }
    data.update(overrides)
    return ChannelManifest(**data)  # type: ignore[arg-type]


def make_record(title: str = "A paper") -> Record:
    return Record(
        channel="fake",
        title=title,
        authors=["Ada"],
        source="Journal",
        year=2024,
        volume="1",
        issue="2",
        pages="3-4",
        doi="10.0/x",
        abstract="Abstract text",
        keywords=["k1"],
    )


@dataclass
class FakeChannel:
    manifest: ChannelManifest
    records: Sequence[Record] = ()
    search_html: str = "<html>ok</html>"
    detail_html: str = "<html>detail</html>"
    journal_html: str = "<html>issue</html>"

    def plan_search(self, query: SearchQuery) -> Plan:
        return Plan(
            channel=self.manifest.channel,
            purpose="search",
            actions=(
                Action("goto", {"url": "https://example.org/search"}),
                Action("read_html"),
            ),
        )

    def parse_search(self, html: str, *, query: SearchQuery) -> SearchPage:
        return SearchPage(records=tuple(self.records), total=len(self.records), page=1)

    def plan_detail(self, url: str) -> Plan:
        return Plan(
            channel=self.manifest.channel,
            purpose="detail",
            actions=(Action("goto", {"url": url}), Action("read_html")),
        )

    def parse_detail(self, html: str, *, url: str) -> Record:
        return make_record()

    def plan_journal(self, *, issn: str, year: int, issue: str) -> Plan:
        return Plan(
            channel=self.manifest.channel,
            purpose="journal",
            actions=(
                Action("goto", {"url": "https://example.org/issue"}),
                Action("read_html"),
            ),
        )

    def parse_journal(self, html: str, *, issn: str, year: int, issue: str) -> SearchPage:
        return SearchPage(records=tuple(self.records))


class StubRegistry:
    def __init__(self, channel: FakeChannel) -> None:
        self._channel = channel
        self.spec = ChannelSpec(
            name=channel.manifest.channel,
            site_version="2026.10",
            manifest=channel.manifest,
            package="tests.fake",
        )

    def select(self, name: str, site_version: str | None = None) -> ChannelSpec:
        return self.spec

    def load(self, name: str, site_version: str | None = None) -> FakeChannel:
        return self._channel
