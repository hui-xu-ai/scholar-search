from __future__ import annotations

from scholar_search.core.export import to_endnote, to_ris
from support import make_record


def test_ris_contains_bibliographic_fields() -> None:
    text = to_ris([make_record()])
    assert "TY  - JOUR" in text
    assert "TI  - A paper" in text
    assert "AU  - Ada" in text
    assert "DO  - 10.0/x" in text
    assert "ER  - " in text


def test_endnote_contains_abstract() -> None:
    text = to_endnote([make_record()])
    assert "%T A paper" in text
    assert "%X Abstract text" in text
    assert "%A Ada" in text


def test_newlines_are_flattened() -> None:
    record = make_record()
    record.abstract = "line one\nline two"
    assert "\nline two" not in to_ris([record])


def test_missing_type_is_generic_not_journal() -> None:
    record = make_record(doc_type=None)
    ris = to_ris([record])
    endnote = to_endnote([record])
    assert "TY  - GEN" in ris
    assert "TY  - JOUR" not in ris
    assert "document type not reported" in ris
    assert "%0 Generic" in endnote


def test_thesis_is_mapped_to_thesis() -> None:
    record = make_record("Thesis", doc_type="thesis")
    assert "TY  - THES" in to_ris([record])
    assert "%0 Thesis" in to_endnote([record])
