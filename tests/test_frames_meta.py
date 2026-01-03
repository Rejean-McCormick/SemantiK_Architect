# tests/test_frames_meta.py
"""
qa/test_frames_meta.py
----------------------

Basic unit tests for the meta / wrapper frame catalogue in
:mod:`semantics.all_frames`.

These tests focus on the *frame type inventory* and family mapping for
meta frames (article, section summary, source / citation). They do not
exercise the full meta-frame dataclasses or any NLG behaviour; those are
covered elsewhere.
"""

from __future__ import annotations

from typing import Dict, List

# [FIX] Use full application path for imports
from app.core.domain.semantics.all_frames import (
    FRAME_FAMILIES,
    FRAME_FAMILY_MAP,
    FrameFamily,
    FrameType,
    family_for_frame,
    infer_frame_type,
)


def test_meta_family_is_present() -> None:
    """The 'meta' family must be present in FRAME_FAMILIES."""
    assert "meta" in FRAME_FAMILIES

    meta_types = FRAME_FAMILIES["meta"]
    assert isinstance(meta_types, list)
    assert len(meta_types) > 0


def test_meta_family_members_are_canonical_and_ordered() -> None:
    """
    The meta family should contain exactly the expected frame types in
    a stable, documented order.
    """
    expected: List[FrameType] = [
        "meta.article",
        "meta.section_summary",
        "meta.source",
    ]

    meta_types = FRAME_FAMILIES["meta"]
    assert meta_types == expected


def test_meta_family_members_are_unique() -> None:
    """No duplicate meta frame_type strings in the catalogue."""
    meta_types = FRAME_FAMILIES["meta"]
    assert len(meta_types) == len(set(meta_types))


def test_meta_types_map_back_to_meta_family() -> None:
    """
    FRAME_FAMILY_MAP must map each meta frame_type back to the 'meta'
    family.
    """
    for ft in FRAME_FAMILIES["meta"]:
        fam: FrameFamily | None = FRAME_FAMILY_MAP.get(ft)
        assert fam == "meta"


def test_family_for_frame_works_with_meta_dicts() -> None:
    """
    family_for_frame should correctly classify dict-like frames that
    declare a meta frame_type.
    """
    for ft in FRAME_FAMILIES["meta"]:
        frame_dict: Dict[str, object] = {"frame_type": ft, "dummy": True}
        fam = family_for_frame(frame_dict, default=None)
        assert fam == "meta"


def test_infer_frame_type_prefers_explicit_frame_type_key() -> None:
    """
    infer_frame_type must return the explicit 'frame_type' string from
    mappings, even when other keys are present.
    """
    frame_dict: Dict[str, object] = {
        "frame_type": "meta.section_summary",
        "heading": "Early life",
        "other": 123,
    }
    ft = infer_frame_type(frame_dict, default=None)
    assert ft == "meta.section_summary"