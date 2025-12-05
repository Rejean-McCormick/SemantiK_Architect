"""
semantics/narrative/reception_impact_frame.py
---------------------------------------------

Narrative / aggregate frame for **reception** and **impact / legacy**.

This frame is intended for sections such as “Reception”, “Legacy”, or
“Impact” in encyclopedic articles. It captures:

- Critical and public reception (who said what, about which aspect, when).
- Domains of impact (which fields or areas were influenced, and how).
- Optional quantitative metrics (box office, citations, ratings, etc.).
- Award events, remakes, key adoptions, and other notable follow-ups.

The frame is designed to be language-agnostic and planner-friendly:
engines and discourse planners can cluster `ReceptionItem`s and
`ImpactDomain`s into 1–3 sentences like:

    - “The film received positive reviews from critics, who praised X but
      criticized Y.”
    - “The theory has had a lasting impact on Z, influencing A and B.”

All surface-form choices are delegated to downstream NLG components
(lexicon, morphology, constructions).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from semantics.types import Entity, Event, TimeSpan


@dataclass
class ReceptionItem:
    """
    One *source × stance × topic* item within reception.

    Examples
    --------
    - A single critic's review (source_entity = that critic or publication).
    - Aggregated public sentiment for a topic (“audiences praised the visuals”).
    - A community or institution’s position on some aspect of the work.

    Fields
    ------
    source_entity:
        Entity representing the source of the reception signal:
        critic, publication, outlet, community, award body, etc.
        May be None if the source is implicit or generic (“critics”, “audiences”).

    stance:
        Coarse label for attitude, e.g.:

            "positive", "mixed", "negative"

        Additional project-specific labels are allowed and preserved.

    topic:
        Optional textual label for the aspect being commented on, e.g.:

            "performance", "script", "visuals", "methodology"

    time:
        Optional `TimeSpan` indicating when the reception occurred
        (release period, review date range, etc.).

    properties:
        Additional structured properties, such as:

            {
                "quote_id": "Q1",
                "rating": 4.5,
                "scale": "stars_5",
                "review_url": "https://example.org/...",
            }
    """

    source_entity: Optional[Entity] = None
    stance: Optional[str] = None
    topic: Optional[str] = None
    time: Optional[TimeSpan] = None
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ImpactDomain:
    """
    One domain / field in which the subject has had an impact.

    Typical domains
    ---------------
    - "physics", "mathematics", "cinema", "literature"
    - "civil rights", "environmental policy"
    - "popular culture", "video games"

    Fields
    ------
    domain:
        Short label for the domain of impact.

    description_properties:
        Bag of properties that can be used by planners / engines to
        describe the impact in more detail, e.g.:

            {
                "description_lemmas": ["influence", "inspiration"],
                "examples": ["Film A", "Movement B"],
                "summary": "Widely cited in later work on X.",
            }

    key_events:
        List of `Event` objects representing concrete manifestations of
        impact, such as:

        - major citations or adoptions,
        - landmark remakes or adaptations,
        - significant policy changes linked to the work/idea.
    """

    domain: str
    description_properties: Dict[str, Any] = field(default_factory=dict)
    key_events: List[Event] = field(default_factory=list)


@dataclass
class ReceptionImpactFrame:
    """
    Narrative frame capturing **reception** and **impact / legacy** for a subject.

    This is a high-level aggregate frame, typically used at the paragraph
    or section level, not for single sentences in isolation.

    Fields
    ------
    frame_type:
        Stable identifier for this frame family. Engines and planners
        can dispatch on this; value is `"reception-impact"`.

    subject_id:
        Optional identifier for the subject of the reception / impact
        (e.g. a Wikidata QID, internal ID, or any stable key). The
        subject itself is usually known from the surrounding article
        context or another frame.

    critical_reception:
        List of `ReceptionItem`s representing critical reception
        (critics, professional reviewers, academic commentary, etc.).

    public_reception:
        List of `ReceptionItem`s representing public or audience
        reception (general audiences, user ratings, fan communities).

    impact_domains:
        List of `ImpactDomain`s describing areas where the work/idea
        has had influence or lasting effect.

    metrics:
        Optional quantitative or categorical metrics, e.g.:

            {
                "box_office_usd": 100_000_000,
                "opening_weekend_usd": 50_000_000,
                "citations_count": 1200,
                "imdb_rating": 7.8,
                "rotten_tomatoes_tomato_meter": 95,
            }

        Exact keys are project-specific; engines may look for a small
        known subset and otherwise ignore unknown metrics.

    awards:
        List of award-related events, represented as `Event` objects
        (e.g. `Event(event_type="award", ...)`), such as:

            - nominations,
            - wins at festivals or ceremonies,
            - prizes and honors.

    extra:
        Free-form metadata bag for pipeline-specific information,
        original JSON, or debugging data that should pass through
        unchanged.
    """

    frame_type: str = "reception-impact"

    subject_id: Optional[str] = None

    # Reception
    critical_reception: List[ReceptionItem] = field(default_factory=list)
    public_reception: List[ReceptionItem] = field(default_factory=list)

    # Impact / legacy
    impact_domains: List[ImpactDomain] = field(default_factory=list)

    # Optional quantitative or categorical metrics
    metrics: Dict[str, Any] = field(default_factory=dict)
    awards: List[Event] = field(default_factory=list)

    extra: Dict[str, Any] = field(default_factory=dict)


__all__ = [
    "ReceptionImpactFrame",
    "ReceptionItem",
    "ImpactDomain",
]
