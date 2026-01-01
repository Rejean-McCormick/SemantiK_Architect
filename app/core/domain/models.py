# app/core/domain/models.py
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, Field

# Unify Frame definition by importing from the authoritative source
from app.core.domain.frame import BaseFrame, BioFrame, EventFrame

# Backward-compatible aliases
Frame = Union[BioFrame, EventFrame, BaseFrame]
SemanticFrame = Frame


# --- Enums ---

class LanguageStatus(str, Enum):
    """Lifecycle status of a language in the system."""
    PLANNED = "planned"       # Defined in config but no files exist
    SCAFFOLDED = "scaffolded" # Directories created, seed files exist
    BUILDING = "building"     # Compilation in progress
    READY = "ready"           # Successfully compiled and loaded
    ERROR = "error"           # Build failed


class GrammarType(str, Enum):
    """The type of grammar engine backing a language."""
    RGL = "rgl"               # Official Resource Grammar Library
    CONTRIB = "contrib"       # Manual contribution (Silver tier)
    FACTORY = "factory"       # Auto-generated Pidgin (Bronze tier)


# --- Entities ---

class Language(BaseModel):
    """
    Represents a supported language in the system.
    Matches the data found in the 'Everything Matrix'.
    """
    # Accept ISO 639-1 or ISO 639-3 (some parts of the system use iso2 keys)
    code: str = Field(
        ...,
        min_length=2,
        max_length=3,
        pattern=r"^[a-z]{2,3}$",
        description="ISO 639-1 or 639-3 code (e.g., 'en', 'fra')",
    )
    name: str = Field(..., min_length=1, description="English name of the language")
    family: Optional[str] = Field(None, description="Language family (e.g., 'Romance')")
    status: LanguageStatus = LanguageStatus.PLANNED
    grammar_type: GrammarType = GrammarType.FACTORY

    # Metadata for tracking build health
    build_strategy: str = Field("fast", pattern=r"^(fast|full)$", description="Build strategy")
    last_build_time: Optional[datetime] = None
    error_log: Optional[str] = None


class Sentence(BaseModel):
    """The output generated text."""
    text: str
    lang_code: str

    # Debug info provided by the engine (e.g., linearization tree)
    debug_info: Optional[Dict[str, Any]] = None

    # Metrics for observability
    generation_time_ms: float = 0.0


class LexiconEntry(BaseModel):
    """Represents a single word in the lexicon."""
    lemma: str
    pos: str  # Part of Speech: N, V, A, etc.
    features: Dict[str, Any] = Field(default_factory=dict)  # Gender, Number, etc.
    source: str = "manual"  # 'wikidata', 'ai', 'manual'
    confidence: float = 1.0


# --- API Payloads ---

class GenerationRequest(BaseModel):
    """
    Input payload for the text generation endpoint.
    (Kept for compatibility; router may accept raw Frame JSON directly.)
    """
    semantic_frame: Frame
    target_language: str = Field(..., min_length=2, max_length=3, description="ISO 639-1 or 639-3")
