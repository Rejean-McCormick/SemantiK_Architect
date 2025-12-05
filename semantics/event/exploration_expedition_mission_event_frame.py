from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from semantics.types import Entity, Event, Location, TimeSpan


@dataclass
class ExplorationExpeditionMissionEventFrame:
    """
    Exploration / expedition / mission event frame.

    High-level semantic frame for Wikipedia-style summaries of **expeditions,
    voyages, and space missions**. Typical subjects include:

        - Polar expeditions
        - Oceanic voyages
        - Mountaineering expeditions
        - Space missions / spaceflights
        - Scientific survey expeditions

    The frame is a **thin, typed wrapper** over a generic `Event` plus a small
    number of fields that are frequent enough to deserve top-level slots.
    Everything else can be stored in `attributes` or in `main_event.properties`.

    Core conventions
    ----------------
    * The expedition / mission itself is represented by `main_event`.
    * Coarse type information is encoded in `mission_kind` and/or
      `main_event.event_type`.
    * Participant roles in `main_event.participants` follow the generic
      conventions from `semantics.roles` (e.g. `"agent"`, `"theme"`, `"crew"`,
      `"sponsor"`, `"leader"`), while this frame exposes the most common
      ones in dedicated fields (`leaders`, `crew`, `sponsoring_organizations`).
    * Route information is captured via `departure_location`, `arrival_location`,
      and `route_locations`.

    Fields
    ------
    frame_type:
        Stable identifier for this frame family: `"exploration-expedition-mission"`.
        Used for debugging and high-level routing.

    main_event:
        Generic `Event` describing the expedition / mission as a whole. Its
        `event_type` is typically a coarse label such as `"expedition"`,
        `"voyage"`, `"exploration"`, or `"space_mission"`.

    mission_kind:
        Optional coarse label classifying the mission, normalized via
        `normalize_mission_kind`. Canonical values include:

            - "expedition"
            - "voyage"
            - "exploration"
            - "space_mission"
            - "mission"  (generic catch-all)

        Additional project-specific labels are allowed and will be preserved.

    leaders:
        List of `Entity` objects representing the main leaders / commanders /
        mission commanders.

    crew:
        List of `Entity` objects representing crew members or participants
        that are not modeled as leaders.

    sponsoring_organizations:
        List of `Entity` objects representing the main sponsoring or organizing
        bodies (e.g. space agencies, navies, research institutions).

    departure_location:
        `Location` from which the expedition or mission departs, where known.

    arrival_location:
        `Location` representing the primary destination or return point, where
        known.

    route_locations:
        Intermediate `Location` objects along the route (ports of call,
        waypoints, bases, landing sites).

    target_locations:
        List of `Location` objects or regions that are the primary target of
        the exploration (e.g. "Antarctica", "Moon", "Mars region X"). These are
        separate from the literal route (ports, launch sites, etc.).

    overall_timespan:
        Coarse `TimeSpan` summarizing when the mission took place. If left
        `None`, it can be filled from `main_event.time` during normalization.

    outcome_summary:
        Short textual label summarizing the overall outcome, e.g.
        "successful", "partially_successful", "failed", or a brief phrase such
        as "first crewed lunar landing".

    discoveries:
        List of `Entity` objects for key discoveries, reached landmarks, or
        surveyed objects associated with the mission (e.g. newly mapped
        regions, celestial bodies, archaeological sites).

    attributes:
        Arbitrary attribute map for additional, mission-specific information
        that is not common enough to warrant a dedicated top-level field.
        Examples:

            {
                "ship_names": ["Endurance", "Terra Nova"],
                "launch_vehicle": Entity(...),
                "landing_site_name": "Sea_of_Tranquility",
            }

    extra:
        Opaque metadata bag for passing through original source structures
        (raw JSON, Wikidata statements, provenance, debugging info, etc.).

    This structure is intentionally **language-agnostic** and contains no
    inflected strings. All surface realization happens downstream via
    lexicon + constructions + engines.
    """

    frame_type: str = "exploration-expedition-mission"
    main_event: Event = field(default_factory=Event)

    mission_kind: Optional[str] = None

    leaders: List[Entity] = field(default_factory=list)
    crew: List[Entity] = field(default_factory=list)
    sponsoring_organizations: List[Entity] = field(default_factory=list)

    departure_location: Optional[Location] = None
    arrival_location: Optional[Location] = None
    route_locations: List[Location] = field(default_factory=list)
    target_locations: List[Location] = field(default_factory=list)

    overall_timespan: Optional[TimeSpan] = None

    outcome_summary: Optional[str] = None
    discoveries: List[Entity] = field(default_factory=list)

    attributes: Dict[str, Any] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Normalize mission_kind into a canonical label when possible.
        self.mission_kind = normalize_mission_kind(self.mission_kind)

        # Ensure all list/dict fields are real mutable containers, not shared
        # defaults or foreign iterables.
        self.leaders = list(self.leaders)
        self.crew = list(self.crew)
        self.sponsoring_organizations = list(self.sponsoring_organizations)
        self.route_locations = list(self.route_locations)
        self.target_locations = list(self.target_locations)
        self.discoveries = list(self.discoveries)

        if not isinstance(self.attributes, dict):
            self.attributes = dict(self.attributes)  # type: ignore[arg-type]
        if not isinstance(self.extra, dict):
            self.extra = dict(self.extra)  # type: ignore[arg-type]

        # If an explicit overall_timespan is not provided, fall back to the
        # core event's time span if available.
        if self.overall_timespan is None and self.main_event.time is not None:
            self.overall_timespan = self.main_event.time


def normalize_mission_kind(kind: Optional[str]) -> Optional[str]:
    """
    Normalize a coarse mission kind label to a canonical form.

    Canonical output values (when applicable)
    ----------------------------------------
    - "expedition"
    - "voyage"
    - "exploration"
    - "space_mission"
    - "mission"

    Any non-empty, unrecognized input is lowercased and spaces are converted
    to underscores, so that project-specific inventories remain stable.

    Examples
    --------
    >>> normalize_mission_kind("Polar expedition")
    'expedition'
    >>> normalize_mission_kind("space mission")
    'space_mission'
    >>> normalize_mission_kind("Spaceflight")
    'space_mission'
    >>> normalize_mission_kind("Survey mission")
    'survey_mission'
    """
    if kind is None:
        return None

    # Basic cleanup
    normalized = kind.strip().lower()
    if not normalized:
        return None

    # Collapse some obvious variants first (spaces / hyphens).
    normalized = normalized.replace("-", " ")

    mapping = {
        # Direct canonical labels
        "expedition": "expedition",
        "voyage": "voyage",
        "exploration": "exploration",
        "mission": "mission",
        "space mission": "space_mission",
        "space_mission": "space_mission",
        # Common paraphrases
        "spaceflight": "space_mission",
        "space flight": "space_mission",
        "lunar mission": "space_mission",
        "moon mission": "space_mission",
        "mars mission": "space_mission",
        "antarctic expedition": "expedition",
        "arctic expedition": "expedition",
        "polar expedition": "expedition",
    }

    if normalized in mapping:
        return mapping[normalized]

    # Default: preserve the text but enforce a consistent format.
    return normalized.replace(" ", "_")


__all__ = ["ExplorationExpeditionMissionEventFrame", "normalize_mission_kind"]
