from __future__ import annotations

from typing import Any, Dict, Literal, Optional, Union

from pydantic import BaseModel, Field, ConfigDict


# --- 1. Shared Entity Model (The "Rich" Subject) ---
class Entity(BaseModel):
    """
    Represents a Discourse Entity with metadata.
    Used for Subjects, Objects, and Agents.
    """
    name: str
    qid: Optional[str] = None
    profession: Optional[str] = None
    nationality: Optional[str] = None
    gender: Optional[str] = None

    # Allow extra fields (flexibility for v2.0)
    model_config = ConfigDict(extra="ignore")


# --- 2. Base Frame ---
class BaseFrame(BaseModel):
    """
    Abstract base class for all Semantic Frames.
    Contains metadata fields used across all intent types.
    """
    context_id: Optional[str] = Field(
        default=None,
        description="UUID linking this frame to a Discourse Session (Redis).",
    )

    # Keep 'style' but accept common synonyms if upstream sends them
    style: Literal["simple", "formal"] = "simple"

    # Metadata for debug/latency tracking
    meta: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


# --- helpers ---
def _get_str_field(obj: Union[Entity, Dict[str, Any]], key: str) -> Optional[str]:
    if isinstance(obj, Entity):
        return getattr(obj, key, None)
    if isinstance(obj, dict):
        v = obj.get(key)
        return v if isinstance(v, str) else None
    return None


def _set_str_field(obj: Union[Entity, Dict[str, Any]], key: str, value: str) -> None:
    if isinstance(obj, Entity):
        setattr(obj, key, value)
    elif isinstance(obj, dict):
        obj[key] = value


# --- 3. BioFrame (Updated for v2.0 Nesting) ---
class BioFrame(BaseFrame):
    """
    Represents an introductory biographical sentence.
    Structure: Subject (Entity) + Bio Attributes.
    """
    frame_type: Literal["bio"] = "bio"

    # Subject is an Entity object or Dict, not flat strings
    subject: Union[Entity, Dict[str, Any]]

    # --- Compatibility Properties (Bridging Nesting vs Router Logic) ---
    @property
    def name(self) -> str:
        """Accessor for the Subject's name."""
        if isinstance(self.subject, Entity):
            return self.subject.name
        return str(self.subject.get("name") or "Unknown")

    @name.setter
    def name(self, value: str) -> None:
        """Mutator for Discourse Planning (Pronominalization)."""
        _set_str_field(self.subject, "name", value)

    @property
    def gender(self) -> Optional[str]:
        return _get_str_field(self.subject, "gender")

    @property
    def qid(self) -> Optional[str]:
        return _get_str_field(self.subject, "qid")


# --- 4. EventFrame ---
class EventFrame(BaseFrame):
    """
    Represents a temporal event.
    Structure: Subject (Entity) + Event Object + Type.
    """
    frame_type: Literal["event"] = "event"

    # Allow Rich Subject (Adapter may send Dict)
    subject: Union[Entity, Dict[str, Any]]

    # Rich or String event object
    event_object: Union[Entity, Dict[str, Any], str]

    # Default to prevent validation errors when upstream omits it
    event_type: str = Field(default="participation", description="Event type key (e.g., 'participation').")

    date: Optional[str] = Field(default=None, description="Year or ISO date string.")
    location: Optional[str] = Field(default=None, description="Key in geography.json.")

    # --- Compatibility Properties ---
    @property
    def name(self) -> str:
        """Accessor for the Subject's name (Logic bridge)."""
        if isinstance(self.subject, Entity):
            return self.subject.name
        return str(self.subject.get("name") or "Unknown")

    @property
    def gender(self) -> Optional[str]:
        return _get_str_field(self.subject, "gender")

    @property
    def qid(self) -> Optional[str]:
        return _get_str_field(self.subject, "qid")


# --- 5. RelationalFrame (Future Proofing) ---
class RelationalFrame(BaseFrame):
    """
    Represents a direct relationship between two entities.
    """
    frame_type: Literal["relational"] = "relational"

    subject: Union[Entity, Dict[str, Any]]
    relation: str = Field(..., description="Predicate key (e.g., 'spouse_of').")
    object: Union[Entity, Dict[str, Any]]

    # --- Compatibility Properties ---
    @property
    def name(self) -> str:
        if isinstance(self.subject, Entity):
            return self.subject.name
        return str(self.subject.get("name") or "Unknown")

    @property
    def gender(self) -> Optional[str]:
        return _get_str_field(self.subject, "gender")

    @property
    def qid(self) -> Optional[str]:
        return _get_str_field(self.subject, "qid")
