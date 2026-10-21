"""Document-type normalisation shared by the search and detail parsers."""

from __future__ import annotations

import pytest

from scholar_search.channels.cnki.v2026_10 import doc_types


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("期刊", "journal"),
        ("期刊论文", "journal"),
        ("中文图书", "book"),
        ("外文期刊", "journal"),
        ("《硕士学位论文》", "thesis"),
        ("《硕士学位论文》网络首发", "thesis"),
        ("期刊（网络首发）", "journal"),
        ("文献类型：期刊（网络首发）", "journal"),
        ("文献类型：中文图书", "book"),
        ("中文会议论文", "conference"),
        ("学报", None),
        ("视频", None),
        ("   ", None),
        (None, None),
    ],
)
def test_normalize_maps_decorated_values(raw: str | None, expected: str | None) -> None:
    assert doc_types.normalize(raw) == expected


def test_unknown_type_is_dropped_not_leaked() -> None:
    # A Chinese type word that we cannot map must not reach the record: the
    # export layer then renders it as generic with a note.
    assert doc_types.normalize("法律法规") is None
