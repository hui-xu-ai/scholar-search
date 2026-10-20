from __future__ import annotations

from scholar_search.core.registry import ChannelRegistry


def test_discovers_cnki_channel() -> None:
    specs = ChannelRegistry().discover()
    cnki = [spec for spec in specs if spec.name == "cnki"]
    assert cnki, "cnki channel must be discoverable"
    assert cnki[0].site_version == "2026.10"
    assert cnki[0].manifest.domains == ("kns.cnki.net", "www.cnki.net")


def test_select_returns_highest_compatible_version() -> None:
    spec = ChannelRegistry().select("cnki")
    assert spec.site_version == "2026.10"


def test_select_missing_channel_raises() -> None:
    try:
        ChannelRegistry().select("nope")
    except Exception as exc:
        assert exc.__class__.__name__ == "ChannelNotFound"
    else:  # pragma: no cover
        raise AssertionError("expected ChannelNotFound")


def test_load_returns_channel_with_manifest() -> None:
    channel = ChannelRegistry().load("cnki")
    assert channel.manifest.channel == "cnki"
    assert channel.manifest.site_version == "2026.10"
