# discourse\state.py
"""
discourse/state.py
------------------

Lightweight discourse state tracking for Semantik Architect.

This module keeps track of:

- Which entities have been mentioned so far.
- Which entity is the current topic.
- Basic salience / recency information for choosing pronouns,
  topic-comment constructions, etc.

It is intentionally simple: enough to support pronoun choice and
topic selection across a short multi-sentence description (e.g. a
Wikipedia lead section).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional

from app.core.domain.semantics.types import Entity


# ---------------------------------------------------------------------------
# Internal entry representation
# ---------------------------------------------------------------------------


@dataclass
class DiscourseEntry:
    """
    Tracking information for a single discourse entity.

    Fields:
        entity:
            The underlying semantic Entity.
        key:
            The internal key used in the discourse map
            (usually entity.id or a derived fallback).
        salience:
            A simple score used for topic/pronoun selection.
            Higher is more salient.
        last_sentence_index:
            Index of the last sentence where this entity was mentioned.
        times_mentioned:
            Count of mentions so far.
        roles:
            Set of semantic roles in which this entity has appeared,
            e.g. {"subject", "object", "topic"}.
        extra:
            Free-form metadata for advanced algorithms.
    """

    entity: Entity
    key: str
    salience: float = 0.0
    last_sentence_index: int = -1
    times_mentioned: int = 0
    roles: set[str] = field(default_factory=set)
    extra: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Discourse state
# ---------------------------------------------------------------------------


class DiscourseState:
    """
    Discourse state for a single document or description.

    Responsibilities:
        - Register entities as they appear.
        - Update salience and last-mention info when an entity is used.
        - Keep track of the current sentence index.
        - Provide helper methods to pick a default topic or look up
          entries by Entity / key.

    This class does not attempt to model full centering theory or
    complex discourse structure. It is a small, pragmatic state
    container for NLG decisions.
    """

    def __init__(self) -> None:
        # sentence_index is incremented by constructions or planner
        # when they move to the next sentence.
        self.sentence_index: int = 0

        # Map: discourse key → DiscourseEntry
        self._entries: Dict[str, DiscourseEntry] = {}

        # Key of current topic entity (if any)
        self._current_topic_key: Optional[str] = None

    # ------------------------------------------------------------------
    # Internal key management
    # ------------------------------------------------------------------

    @staticmethod
    def _make_key(entity: Entity) -> str:
        """
        Derive a stable discourse key for an Entity.

        Priority:
            1. entity.id, if present
            2. entity.name.lower()
        """
        if entity.id:
            return str(entity.id)
        # Fallback: use lowercase name as key
        return entity.name.strip().lower() or "_anonymous"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register_entity(
        self,
        entity: Entity,
        *,
        initial_salience: float = 1.0,
        as_topic: bool = False,
        roles: Optional[Iterable[str]] = None,
    ) -> DiscourseEntry:
        """
        Ensure an entity is known to the discourse state.

        If already registered, this does NOT reset its salience; it
        simply returns the existing entry.

        Args:
            entity:
                The entity to register.
            initial_salience:
                Starting salience if the entity is new.
            as_topic:
                If True and the entity is new, mark it as the current topic.
            roles:
                Optional iterable of initial roles for this entity.

        Returns:
            DiscourseEntry for the entity.
        """
        key = self._make_key(entity)
        entry = self._entries.get(key)

        if entry is None:
            entry = DiscourseEntry(
                entity=entity,
                key=key,
                salience=float(initial_salience),
                last_sentence_index=self.sentence_index,
                times_mentioned=0,
            )
            if roles:
                entry.roles.update(roles)
            self._entries[key] = entry

            if as_topic:
                self._current_topic_key = key

        return entry

    def mention(
        self,
        entity: Entity,
        *,
        role: Optional[str] = None,
        as_topic: bool = False,
        salience_boost: float = 1.0,
    ) -> DiscourseEntry:
        """
        Record a mention of an entity in the current sentence.

        This will:
            - Register the entity if not already known.
            - Update its salience, last_sentence_index and times_mentioned.
            - Optionally mark it as topic.

        Args:
            entity:
                The mentioned entity.
            role:
                Optional semantic role label ("subject", "object", "topic"...).
            as_topic:
                If True, mark this entity as the current topic.
            salience_boost:
                Amount by which to increase salience for this mention.

        Returns:
            Updated DiscourseEntry.
        """
        entry = self.register_entity(entity)

        entry.times_mentioned += 1
        entry.last_sentence_index = self.sentence_index
        entry.salience += float(salience_boost)

        if role:
            entry.roles.add(role)

        if as_topic:
            self._current_topic_key = entry.key

        return entry

    def advance_sentence(self, decay: float = 0.9) -> None:
        """
        Move to the next sentence and apply a simple salience decay.

        Args:
            decay:
                Multiplicative decay factor applied to all entries'
                salience after advancing the sentence index.
        """
        self.sentence_index += 1

        for entry in self._entries.values():
            entry.salience *= float(decay)

    # ------------------------------------------------------------------
    # Topic / salience queries
    # ------------------------------------------------------------------

    def get_current_topic(self) -> Optional[Entity]:
        """
        Return the Entity currently treated as topic, if any.
        """
        if not self._current_topic_key:
            return None
        entry = self._entries.get(self._current_topic_key)
        return entry.entity if entry else None

    def set_current_topic(self, entity: Entity) -> None:
        """
        Explicitly set the current topic to the given entity.
        """
        entry = self.register_entity(entity, as_topic=True)
        self._current_topic_key = entry.key

    def get_or_choose_topic(self) -> Optional[Entity]:
        """
        Return the current topic if known, otherwise choose a reasonable
        default based on salience.

        Default strategy:
            - If a topic is set and still tracked, return it.
            - Else, pick the entity with the highest salience.
        """
        topic = self.get_current_topic()
        if topic is not None:
            return topic

        if not self._entries:
            return None

        # Pick highest-salience entry
        entry = max(self._entries.values(), key=lambda e: e.salience)
        self._current_topic_key = entry.key
        return entry.entity

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------

    def get_entry_by_entity(self, entity: Entity) -> Optional[DiscourseEntry]:
        """
        Find the discourse entry corresponding to the given entity, if any.
        """
        key = self._make_key(entity)
        return self._entries.get(key)

    def get_entry_by_key(self, key: str) -> Optional[DiscourseEntry]:
        """
        Find the discourse entry corresponding to the given internal key.
        """
        return self._entries.get(key)

    def all_entries(self) -> Dict[str, DiscourseEntry]:
        """
        Return a shallow copy of the entries mapping (for debugging /
        inspection purposes).
        """
        return dict(self._entries)


__all__ = ["DiscourseState", "DiscourseEntry"]
