from typing import Optional, Literal, Dict, Any, Union
from pydantic import BaseModel, Field

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
    class Config:
        extra = "ignore" 

# --- 2. Base Frame ---
class BaseFrame(BaseModel):
    """
    Abstract base class for all Semantic Frames.
    Contains metadata fields used across all intent types.
    """
    context_id: Optional[str] = Field(
        default=None, 
        description="UUID linking this frame to a Discourse Session (Redis)."
    )
    style: Literal["simple", "formal"] = "simple"
    
    # Metadata for debug/latency tracking
    meta: Dict[str, Any] = Field(default_factory=dict)

# --- 3. BioFrame (Updated for v2.0 Nesting) ---
class BioFrame(BaseFrame):
    """
    Represents an introductory biographical sentence.
    Structure: Subject (Entity) + Bio Attributes.
    """
    frame_type: Literal["bio"] = "bio"
    
    # V2 Change: Subject is now an Entity object or Dict, not flat strings
    subject: Union[Entity, Dict[str, Any]]
    
    # --- Compatibility Properties (Bridging Nesting vs Router Logic) ---
    @property
    def name(self) -> str:
        """Accessor for the Subject's name."""
        if isinstance(self.subject, Entity):
            return self.subject.name
        return self.subject.get("name", "Unknown")

    @name.setter
    def name(self, value: str):
        """Mutator for Discourse Planning (Pronominalization)."""
        if isinstance(self.subject, Entity):
            self.subject.name = value
        elif isinstance(self.subject, dict):
            self.subject["name"] = value

    @property
    def gender(self) -> Optional[str]:
        if isinstance(self.subject, Entity):
            return self.subject.gender
        return self.subject.get("gender")

# --- 4. EventFrame (The Fix) ---
class EventFrame(BaseFrame):
    """
    Represents a temporal event.
    Structure: Subject (Entity) + Event Object + Type.
    """
    frame_type: Literal["event"] = "event"
    
    # Fix A: Allow Rich Subject (Adapter sends Dict)
    subject: Union[Entity, Dict[str, Any]]
    
    # Fix B: Add Object field (Rich or String)
    event_object: Union[Entity, Dict[str, Any], str]
    
    # Fix C: Default 'event_type' to prevent validation errors
    # (Ninai often implies this contextually)
    event_type: str = "participation"
    
    date: Optional[str] = Field(default=None, description="Year or ISO date string.")
    location: Optional[str] = Field(default=None, description="Key in geography.json.")

    # --- Compatibility Properties ---
    @property
    def name(self) -> str:
        """Accessor for the Subject's name (Logic bridge)."""
        if isinstance(self.subject, Entity):
            return self.subject.name
        return self.subject.get("name", "Unknown")

# --- 5. RelationalFrame (Future Proofing) ---
class RelationalFrame(BaseFrame):
    """
    Represents a direct relationship between two entities.
    """
    frame_type: Literal["relational"] = "relational"
    
    subject: Union[Entity, Dict[str, Any]]
    relation: str = Field(..., description="Predicate key (e.g., 'spouse_of').")
    object: Union[Entity, Dict[str, Any]]