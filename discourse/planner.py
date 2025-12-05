"""
discourse/planner.py
--------------------

Lightweight discourse planner for multi-sentence output.

Goal
====
Given a list of *semantic frames* (e.g. for a biography), decide:

- In which order to realize them as sentences.
- Which construction to use for each frame (at a coarse level).
- Basic information-structure hints (who is topic, what is focus).

The planner is intentionally:

- Domain-focused: for now, primarily tuned for **biographical** data.
- Heuristic: no heavy AI / statistics; just sensible rule-based ordering.
- Decoupled: it does NOT render text and does NOT depend on router;
  it only returns a structured plan that the caller can render.

Expected frame shape
====================

We assume each frame is a dict-like object with at least:

    {
        "frame_type": "definition" | "birth" | "death" | "career" | ...,
        "main_entity_id": "Q123",     # optional
        "subject_id": "Q123",         # optional (fallback)
        "priority": 0,                # optional, int; lower = earlier
        ...
    }

This is intentionally loose; you can adapt your semantic layer to produce
whatever fields you need as long as they satisfy these conventions.

Output shape
============

The planner returns a list of `PlannedSentence` objects, each containing:

- `frame`: the original frame object
- `construction_id`: string, e.g. "copula_equative_simple"
- `topic_entity_id`: who is the discourse topic for this sentence (if any)
- `focus_role`: simple label of what is focussed ("role", "event", etc.)
- `metadata`: free-form dict for additional hints (e.g. "sentence_kind")

Rendering
=========

A typical call chain is:

    frames = [ ... ]  # semantic frames for a person
    plan = plan_biography(frames, lang_code="fr")
    for sentence in plan:
        surface = router.render(
            construction_id=sentence.construction_id,
            slots=build_slots(sentence.frame, sentence.topic_entity_id),
            lang_code="fr",
        )

The exact slot-building logic is up to your semantics → constructions bridge.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class PlannedSentence:
    """
    A single sentence-level plan.

    Attributes:
        frame:
            The original semantic frame (dict-like or object).
        construction_id:
            Which construction to use, e.g. "copula_equative_simple".
        topic_entity_id:
            Optional ID of the discourse topic for this sentence.
        focus_role:
            Optional label for what is in focus (e.g. "role", "achievement").
        metadata:
            Extra hints (e.g. {"sentence_kind": "definition"}).
    """

    frame: Any
    construction_id: str
    topic_entity_id: Optional[str] = None
    focus_role: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


# Default order for biography-oriented frame types
BIO_FRAME_ORDER: List[str] = [
    "definition",  # core identity: "X is a Y"
    "biographical-definition",  # alias / more specific label
    "birth",  # "X was born in Y in YEAR"
    "education",
    "career",
    "achievement",
    "award",
    "position",
    "death",
    "other",
]


def _frame_type(frame: Any) -> str:
    """
    Extract frame_type from a frame.

    We treat any non-string / missing type as "other".
    """
    if isinstance(frame, dict):
        ft = frame.get("frame_type")
    else:
        ft = getattr(frame, "frame_type", None)
    if not isinstance(ft, str):
        return "other"
    return ft


def _main_entity_id(frame: Any) -> Optional[str]:
    """
    Extract the main entity ID for a frame.

    We try common keys in order:
        - "main_entity_id"
        - "subject_id"
        - "entity_id"
    """
    if isinstance(frame, dict):
        for key in ("main_entity_id", "subject_id", "entity_id"):
            val = frame.get(key)
            if val:
                return str(val)
    else:
        for attr in ("main_entity_id", "subject_id", "entity_id"):
            if hasattr(frame, attr):
                val = getattr(frame, attr)
                if val:
                    return str(val)
    return None


def _explicit_priority(frame: Any) -> Optional[int]:
    """
    Read an explicit 'priority' field if present.

    Lower numbers are scheduled earlier. If not present, returns None.
    """
    if isinstance(frame, dict):
        val = frame.get("priority")
    else:
        val = getattr(frame, "priority", None)
    if isinstance(val, int):
        return val
    # treat numeric strings as ints as well
    try:
        return int(val)  # type: ignore[arg-type]
    except Exception:
        return None


def _frame_type_rank(ftype: str, order: Sequence[str]) -> int:
    """
    Map a frame_type string to a rank index in a given type order.
    Unknown types are placed after all known types.
    """
    try:
        return order.index(ftype)
    except ValueError:
        return len(order)


def _guess_construction_id(frame_type: str) -> str:
    """
    Guess a construction ID from a biography-oriented frame_type.

    This mapping is deliberately simple and can be extended as needed.
    """
    mapping = {
        "definition": "copula_equative_simple",
        "biographical-definition": "copula_equative_simple",
        "position": "copula_equative_simple",
        "birth": "intransitive_event",
        "death": "intransitive_event",
        "career": "intransitive_event",
        "achievement": "transitive_event",
        "award": "ditransitive_event",
    }
    return mapping.get(frame_type, "copula_equative_simple")


def _guess_focus_role(frame_type: str) -> Optional[str]:
    """
    Provide a coarse label for what is in focus in this sentence.

    This is primarily meant as a hint for downstream constructions
    (e.g. for focus particles or sentence packaging).
    """
    if frame_type in ("definition", "biographical-definition", "position"):
        return "role"
    if frame_type in ("birth", "death"):
        return "event_time_place"
    if frame_type in ("achievement", "award"):
        return "achievement"
    if frame_type == "career":
        return "career"
    return None


# ---------------------------------------------------------------------------
# Public planner API
# ---------------------------------------------------------------------------


def plan_biography(
    frames: Iterable[Any],
    *,
    lang_code: str,
) -> List[PlannedSentence]:
    """
    Plan a multi-sentence biography from a sequence of frames.

    Heuristics:
        - Sort frames primarily by:
            1. explicit `priority` (if provided),
            2. default BIO_FRAME_ORDER,
            3. original input order (stable tiebreak).
        - For each frame, choose:
            - a default construction_id,
            - a simple focus label.
        - Topic:
            - The main entity of the *first* definition-like frame is treated
              as the discourse topic for all subsequent sentences that share
              the same entity id.
            - Other frames may have topic_entity_id left as None.

    Args:
        frames:
            Iterable of semantic frames (dict-like or objects).
        lang_code:
            Currently unused by the planner, but reserved for future
            language-specific ordering tweaks.

    Returns:
        List of `PlannedSentence` objects in the intended linear order.
    """
    frame_list = list(frames)
    indexed: List[Tuple[int, Any]] = list(enumerate(frame_list))

    # Compute sort keys
    sort_keys: List[Tuple[Tuple[int, int, int], Any]] = []

    for idx, frame in indexed:
        ftype = _frame_type(frame)
        fprio = _explicit_priority(frame)
        type_rank = _frame_type_rank(ftype, BIO_FRAME_ORDER)
        # explicit priority beats type rank, both beat original index
        priority = fprio if fprio is not None else type_rank
        sort_keys.append(((priority, type_rank, idx), frame))

    # Stable sort by composite key
    sort_keys.sort(key=lambda kv: kv[0])
    sorted_frames = [frame for (_, frame) in sort_keys]

    # Determine the main entity for definition-like frames
    topic_entity_id: Optional[str] = None
    for frame in sorted_frames:
        ftype = _frame_type(frame)
        if ftype in ("definition", "biographical-definition"):
            topic_entity_id = _main_entity_id(frame)
            if topic_entity_id:
                break

    planned: List[PlannedSentence] = []

    for frame in sorted_frames:
        ftype = _frame_type(frame)
        main_entity = _main_entity_id(frame)

        construction_id = _guess_construction_id(ftype)
        focus_role = _guess_focus_role(ftype)

        # Topic decision:
        #   If main_entity matches the biography's main topic (if any),
        #   we mark it as topic; otherwise we leave it None.
        sent_topic: Optional[str] = None
        if topic_entity_id and main_entity and main_entity == topic_entity_id:
            sent_topic = topic_entity_id

        planned.append(
            PlannedSentence(
                frame=frame,
                construction_id=construction_id,
                topic_entity_id=sent_topic,
                focus_role=focus_role,
                metadata={"sentence_kind": ftype},
            )
        )

    return planned


def plan_generic(
    frames: Iterable[Any],
    *,
    lang_code: str,
    domain: str = "auto",
) -> List[PlannedSentence]:
    """
    Generic entrypoint for discourse planning.

    For now, this is a thin wrapper:

        - If domain == "bio" or we detect biography-oriented frames,
          delegate to `plan_biography`.
        - Otherwise, keep the original order and assign a default
          construction to each frame.

    This allows you to plug in other planners later (e.g. news, sports).
    """
    frame_list = list(frames)

    if domain == "bio" or _looks_like_biography(frame_list):
        return plan_biography(frame_list, lang_code=lang_code)

    # Fallback: preserve input order, use a neutral construction
    planned: List[PlannedSentence] = []
    for frame in frame_list:
        ftype = _frame_type(frame)
        planned.append(
            PlannedSentence(
                frame=frame,
                construction_id=_guess_construction_id(ftype),
                topic_entity_id=_main_entity_id(frame),
                focus_role=_guess_focus_role(ftype),
                metadata={"sentence_kind": ftype},
            )
        )
    return planned


def _looks_like_biography(frames: Sequence[Any]) -> bool:
    """
    Heuristic detection of a biographical domain based on frame types.
    """
    bioish = {"definition", "biographical-definition", "birth", "death", "career"}
    for frame in frames:
        if _frame_type(frame) in bioish:
            return True
    return False


__all__ = [
    "PlannedSentence",
    "plan_biography",
    "plan_generic",
]
