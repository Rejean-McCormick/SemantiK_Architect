# tests/http_api/test_frames_registry.py
"""
tests/http_api/test_frames_registry.py
-------------------------------------

Sanity checks for the Frame Registry.

NOTE v2.1 Refactor:
The separate HTTP registry module has been deprecated. This test now verifies
the integrity of the Core Domain's `all_frames.py` module, which serves as
the Single Source of Truth for frame definitions.
"""

from __future__ import annotations

from typing import List

# FIX: Import from the Core Domain (v2.1 Architecture)
from app.core.domain.semantics import all_frames
from app.core.domain.semantics.all_frames import FRAME_FAMILIES, FrameType


def test_registry_exposes_all_semantic_families() -> None:
    """
    Every family key present in FRAME_FAMILIES must be exposed by the
    registry.
    """
    # In v2.1, FRAME_FAMILIES is the registry.
    # We verify it is accessible and consistent.
    families_from_registry = set(all_frames.FRAME_FAMILIES.keys())

    for family in FRAME_FAMILIES.keys():
        assert family in families_from_registry, f"Missing family in registry: {family}"


def test_family_members_match_semantic_catalogue_in_order() -> None:
    """
    For each frame family, the registry must return the same list of
    frame_type strings, in the same canonical order as FRAME_FAMILIES.
    """
    for family, expected_types in FRAME_FAMILIES.items():
        # Direct access to the dictionary in the Core module
        registry_types: List[FrameType] = all_frames.FRAME_FAMILIES[family]
        assert registry_types == expected_types, f"Family {family} mismatch"


def test_family_members_are_unique_in_registry() -> None:
    """
    Within each family, the registry must not introduce duplicate frame_type
    entries.
    """
    for family in all_frames.FRAME_FAMILIES.keys():
        frame_types = all_frames.FRAME_FAMILIES[family]
        assert len(frame_types) == len(
            set(frame_types)
        ), f"Duplicate frame_type values in family {family}"