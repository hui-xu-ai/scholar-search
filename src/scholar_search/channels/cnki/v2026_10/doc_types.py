"""Canonical document-type tokens shared by the CNKI parsers.

CNKI reports a record's type in several places — the result grid's ``td.data``
cell, the detail header's 文献类型 row, ``.doc-top`` — and the wording carries
language prefixes ("中文图书"), wrappers ("《期刊》") and status suffixes
("（网络首发）"). Both parsers normalise through :func:`normalize`, so a record
never stores raw site text as its type and the export mapping always sees a
token it knows.
"""

from __future__ import annotations

CANONICAL: dict[str, str] = {
    "期刊": "journal",
    "期刊论文": "journal",
    "学术期刊": "journal",
    "学位论文": "thesis",
    "硕士": "thesis",
    "硕士学位论文": "thesis",
    "博士": "thesis",
    "博士学位论文": "thesis",
    "会议": "conference",
    "会议论文": "conference",
    "报纸": "newspaper",
    "图书": "book",
    "专著": "book",
    "专利": "patent",
    "标准": "standard",
    "年鉴": "yearbook",
    "成果": "achievement",
    "科技成果": "achievement",
}

# The grid and the detail header both prefix the type with a language, and both
# wrap it in brackets once in a while.
_PREFIXES: tuple[str, ...] = ("中文", "外文", "西文", "英文", "日文", "俄文")
_STATUS_WORDS: tuple[str, ...] = ("网络首发", "优先出版", "网络出版", "附视频")
_WRAPPERS = "《》〈〉()（）[]【】"
LABELS: frozenset[str] = frozenset({"文献类型", "文献类别", "资源类型", "类型"})


def _strip_label(text: str) -> str:
    label, separator, value = text.partition(":")
    return value if separator and label in LABELS else text


def normalize(raw: str | None) -> str | None:
    """Return the canonical token, or ``None`` when the value is not a type.

    ``None`` is deliberate: the export layer renders an unknown type as generic
    with a note, which is honest, while a leaked Chinese string would become a
    meaningless record field.
    """

    if not raw:
        return None
    text = _strip_label("".join(raw.split()).replace("：", ":"))
    text = "".join(char for char in text if char not in _WRAPPERS)
    for word in _STATUS_WORDS:
        text = text.replace(word, "")
    for _ in range(2):
        prefix = next(
            (item for item in _PREFIXES if text.startswith(item) and len(text) > len(item)),
            None,
        )
        if prefix is None:
            break
        text = text[len(prefix) :]
    return CANONICAL.get(text)
