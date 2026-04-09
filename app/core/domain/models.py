from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

Style = Literal["simple", "formal"]


def _clean_optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return str(value).strip() or None


def _coerce_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    try:
        return dict(value)
    except Exception:
        return {}


def _coerce_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    out: list[str] = []
    if isinstance(value, (list, tuple, set)):
        for item in value:
            cleaned = _clean_optional_str(item)
            if cleaned:
                out.append(cleaned)
    return out


def _normalize_lang_code(value: Any) -> str:
    cleaned = _clean_optional_str(value)
    if not cleaned:
        raise ValueError("language code is required")
    normalized = cleaned.lower()
    if not normalized.isalpha() or len(normalized) not in {2, 3}:
        raise ValueError("language code must be a 2- or 3-letter alphabetic code")
    return normalized


def _normalize_frame_type(value: Any) -> str:
    cleaned = _clean_optional_str(value)
    return (cleaned or "generic").lower()


def _is_bio_like_frame_type(frame_type: str) -> bool:
    return frame_type in {"bio", "person", "entity.person", "human"} or frame_type.startswith(
        "bio."
    )


def _is_event_like_frame_type(frame_type: str) -> bool:
    return frame_type == "event" or frame_type.startswith("event.")


def _is_relation_like_frame_type(frame_type: str) -> bool:
    return (
        frame_type in {"relational", "relation", "attribute", "comparison"}
        or frame_type.startswith("rel.")
        or frame_type.startswith("relation.")
        or frame_type.startswith("relational.")
    )


def _best_name(entity: Any) -> str:
    if isinstance(entity, dict):
        value = entity.get("name") or entity.get("label")
        if isinstance(value, str) and value.strip():
            return value.strip()
    if isinstance(entity, str):
        cleaned = entity.strip()
        if cleaned:
            return cleaned
    for attr in ("name", "label"):
        value = getattr(entity, attr, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _entity_attr(entity: Any, key: str) -> Optional[str]:
    if isinstance(entity, dict):
        value = entity.get(key)
        return _clean_optional_str(value)
    return _clean_optional_str(getattr(entity, key, None))


def _merge_subject_dicts(*parts: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for part in parts:
        for key, value in part.items():
            if value is None:
                continue
            if isinstance(value, str):
                cleaned = value.strip()
                if not cleaned:
                    continue
                merged[key] = cleaned
            else:
                merged[key] = value
    return merged


# ---------------------------------------------------------------------------
# Runtime/public result models
# ---------------------------------------------------------------------------


class SurfaceResult(BaseModel):
    """
    Canonical runtime output.

    This aligns with the planner-first contract and the public response envelope:
      text, lang_code, construction_id, renderer_backend, fallback_used,
      tokens, debug_info, generation_time_ms.
    """

    text: str
    lang_code: str
    construction_id: str = "unknown"
    renderer_backend: str = "compat"
    fallback_used: bool = False
    tokens: list[str] = Field(default_factory=list)
    debug_info: dict[str, Any] = Field(default_factory=dict)
    generation_time_ms: float = 0.0

    model_config = ConfigDict(
        extra="ignore",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    @field_validator("text")
    @classmethod
    def _validate_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("text must be a non-empty string")
        return cleaned

    @field_validator("lang_code", mode="before")
    @classmethod
    def _normalize_lang_code_field(cls, value: Any) -> str:
        return _normalize_lang_code(value)

    @field_validator("construction_id", "renderer_backend", mode="before")
    @classmethod
    def _normalize_required_labels(cls, value: Any) -> str:
        cleaned = _clean_optional_str(value)
        if not cleaned:
            raise ValueError("field must be a non-empty string")
        return cleaned

    @field_validator("tokens", mode="before")
    @classmethod
    def _normalize_tokens(cls, value: Any) -> list[str]:
        return _coerce_str_list(value)

    @field_validator("debug_info", mode="before")
    @classmethod
    def _normalize_debug_info(cls, value: Any) -> dict[str, Any]:
        return _coerce_mapping(value)

    @field_validator("generation_time_ms", mode="before")
    @classmethod
    def _normalize_generation_time_ms(cls, value: Any) -> float:
        try:
            return float(value or 0.0)
        except Exception:
            return 0.0

    @model_validator(mode="after")
    def _finalize_runtime_contract(self) -> "SurfaceResult":
        if not self.tokens:
            self.tokens = self.text.split()

        debug = dict(self.debug_info)

        debug["lang_code"] = self.lang_code
        debug["construction_id"] = self.construction_id
        debug["renderer_backend"] = self.renderer_backend
        debug["fallback_used"] = self.fallback_used
        debug.setdefault("runtime_path", "compat")
        debug.setdefault("slot_keys", [])
        debug.setdefault("selected_backend", self.renderer_backend)
        debug.setdefault("attempted_backends", [self.renderer_backend])

        self.debug_info = debug
        return self


# Backward-compatible alias used throughout the repo/tests.
Sentence = SurfaceResult


# ---------------------------------------------------------------------------
# Frame models
# ---------------------------------------------------------------------------


class BaseFrame(BaseModel):
    """
    Common wire-frame fields shared by all API/runtime frame shapes.
    """

    context_id: Optional[str] = Field(default=None)
    style: Style = Field(default="simple")
    properties: dict[str, Any] = Field(default_factory=dict)
    meta: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_common_payload(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        raw = dict(data)

        style_in = raw.get("style", raw.get("register"))
        if isinstance(style_in, str):
            normalized = style_in.strip().lower()
            if normalized in {"neutral", "plain"}:
                normalized = "simple"
            if normalized in {"simple", "formal"}:
                raw["style"] = normalized

        raw["context_id"] = _clean_optional_str(raw.get("context_id"))
        raw["properties"] = _coerce_mapping(raw.get("properties"))
        raw["meta"] = _coerce_mapping(raw.get("meta"))
        return raw

    @field_validator("style", mode="before")
    @classmethod
    def _normalize_style(cls, value: Any) -> Style:
        cleaned = (_clean_optional_str(value) or "simple").lower()
        if cleaned in {"neutral", "plain"}:
            cleaned = "simple"
        if cleaned not in {"simple", "formal"}:
            raise ValueError("style must be one of: simple, formal")
        return cleaned  # type: ignore[return-value]

    @field_validator("context_id", mode="before")
    @classmethod
    def _normalize_context_id(cls, value: Any) -> Any:
        return _clean_optional_str(value)

    @field_validator("properties", "meta", mode="before")
    @classmethod
    def _normalize_dict_fields(cls, value: Any) -> dict[str, Any]:
        return _coerce_mapping(value)


class Frame(BaseFrame):
    """
    Compatibility frame accepted by runtime code, tests, and API normalization.

    This is intentionally permissive and can normalize:
      - canonical `bio` payloads,
      - flat `entity.person` payloads,
      - compatibility `main_entity` + lemma-list shapes,
      - generic event/relational payloads.
    """

    frame_type: str = Field(default="generic")
    subject: Optional[dict[str, Any]] = Field(default=None)
    main_entity: Optional[dict[str, Any]] = Field(default=None)
    primary_profession_lemmas: list[str] = Field(default_factory=list)
    nationality_lemmas: list[str] = Field(default_factory=list)
    event: Optional[dict[str, Any]] = Field(default=None)

    @model_validator(mode="before")
    @classmethod
    def _normalize_frame_payload(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        raw = dict(data)
        raw["frame_type"] = _normalize_frame_type(raw.get("frame_type"))

        raw["subject"] = _coerce_mapping(raw.get("subject")) or None
        raw["main_entity"] = _coerce_mapping(raw.get("main_entity")) or None
        raw["event"] = _coerce_mapping(raw.get("event")) or None
        raw["primary_profession_lemmas"] = _coerce_str_list(raw.get("primary_profession_lemmas"))
        raw["nationality_lemmas"] = _coerce_str_list(raw.get("nationality_lemmas"))

        properties = _coerce_mapping(raw.get("properties"))
        meta = _coerce_mapping(raw.get("meta"))

        # Promote main_entity into subject for compatibility.
        if raw["main_entity"] and not raw["subject"]:
            raw["subject"] = dict(raw["main_entity"])

        # Accept flat person-like payloads.
        flat_subject: dict[str, Any] = {}
        for key in ("name", "label", "profession", "nationality", "gender", "qid"):
            cleaned = _clean_optional_str(raw.get(key))
            if cleaned:
                canonical_key = "name" if key == "label" else key
                flat_subject[canonical_key] = cleaned

        if _is_bio_like_frame_type(raw["frame_type"]) or flat_subject:
            raw["subject"] = _merge_subject_dicts(raw["subject"] or {}, raw["main_entity"] or {}, flat_subject)

            # Mirror common bio/person keys into properties for downstream compatibility.
            for key in ("name", "profession", "nationality", "gender", "qid"):
                value = raw["subject"].get(key) if raw["subject"] else None
                if value is not None:
                    properties[key] = value

            if raw["primary_profession_lemmas"]:
                properties["primary_profession_lemmas"] = list(raw["primary_profession_lemmas"])
                properties.setdefault("profession", raw["primary_profession_lemmas"][0])

            if raw["nationality_lemmas"]:
                properties["nationality_lemmas"] = list(raw["nationality_lemmas"])
                properties.setdefault("nationality", raw["nationality_lemmas"][0])

        raw["properties"] = properties
        raw["meta"] = meta
        return raw

    @field_validator("frame_type", mode="before")
    @classmethod
    def _normalize_frame_type_field(cls, value: Any) -> str:
        return _normalize_frame_type(value)

    @field_validator("subject", "main_entity", "event", mode="before")
    @classmethod
    def _normalize_optional_mapping_fields(cls, value: Any) -> Optional[dict[str, Any]]:
        mapped = _coerce_mapping(value)
        return mapped or None

    @field_validator("primary_profession_lemmas", "nationality_lemmas", mode="before")
    @classmethod
    def _normalize_lemma_lists(cls, value: Any) -> list[str]:
        return _coerce_str_list(value)

    @model_validator(mode="after")
    def _validate_bio_like_requirements(self) -> "Frame":
        if self.is_bio_like and not self.subject:
            raise ValueError("bio-like frames require subject or flat person fields")
        return self

    @property
    def normalized_frame_type(self) -> str:
        if _is_bio_like_frame_type(self.frame_type):
            return "bio"
        if _is_event_like_frame_type(self.frame_type):
            return "event"
        if _is_relation_like_frame_type(self.frame_type):
            return "relational"
        return self.frame_type

    @property
    def is_bio_like(self) -> bool:
        return self.normalized_frame_type == "bio"

    @property
    def is_event_like(self) -> bool:
        return self.normalized_frame_type == "event"

    @property
    def is_relation_like(self) -> bool:
        return self.normalized_frame_type == "relational"

    @property
    def name(self) -> str:
        return _best_name(self.subject or self.main_entity or {})

    @property
    def gender(self) -> Optional[str]:
        return _entity_attr(self.subject or self.main_entity or {}, "gender")

    @property
    def qid(self) -> Optional[str]:
        return _entity_attr(self.subject or self.main_entity or {}, "qid")

    @property
    def subject_name(self) -> str:
        return self.name

    @property
    def subject_qid(self) -> Optional[str]:
        return self.qid


class BioFrame(Frame):
    frame_type: Literal["bio"] = "bio"
    subject: dict[str, Any]

    @model_validator(mode="after")
    def _validate_subject(self) -> "BioFrame":
        if not self.subject:
            raise ValueError("BioFrame requires a subject")
        return self


class EventFrame(Frame):
    frame_type: Literal["event"] = "event"
    subject: dict[str, Any]
    event_object: Any = Field(default=None)
    event_type: str = Field(default="participation")
    date: Optional[str] = Field(default=None)
    location: Optional[str] = Field(default=None)

    @model_validator(mode="before")
    @classmethod
    def _normalize_event_payload(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        raw = dict(data)

        if "event_object" not in raw:
            for alias in ("object", "target", "patient", "theme"):
                if alias in raw:
                    raw["event_object"] = raw[alias]
                    break

        if "event_type" not in raw:
            for alias in ("type", "kind"):
                cleaned = _clean_optional_str(raw.get(alias))
                if cleaned:
                    raw["event_type"] = cleaned
                    break

        raw["date"] = _clean_optional_str(raw.get("date"))
        raw["location"] = _clean_optional_str(raw.get("location"))
        return raw

    @field_validator("event_type")
    @classmethod
    def _validate_event_type(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("event_type must be a non-empty string")
        return cleaned


class RelationalFrame(Frame):
    frame_type: Literal["relational"] = "relational"
    subject: dict[str, Any]
    relation: str
    object: dict[str, Any]

    @model_validator(mode="before")
    @classmethod
    def _normalize_relational_payload(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        raw = dict(data)

        if "object" not in raw:
            for alias in ("target", "right", "other"):
                if alias in raw:
                    raw["object"] = raw[alias]
                    break

        raw["relation"] = _clean_optional_str(raw.get("relation"))
        return raw

    @field_validator("relation")
    @classmethod
    def _validate_relation(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("relation must be a non-empty string")
        return cleaned


# ---------------------------------------------------------------------------
# Language / lexicon models
# ---------------------------------------------------------------------------


class LanguageStatus(str, Enum):
    PLANNED = "planned"
    BUILDING = "building"
    READY = "ready"
    ERROR = "error"
    DISABLED = "disabled"


class GrammarType(str, Enum):
    FACTORY = "factory"
    RGL = "rgl"
    GF = "gf"
    LEGACY = "legacy"


class Language(BaseModel):
    code: str
    name: str
    status: LanguageStatus = LanguageStatus.PLANNED
    grammar_type: GrammarType = GrammarType.FACTORY
    build_strategy: str = "fast"
    family: Optional[str] = None
    last_build_time: Optional[str] = None
    error_log: Optional[str] = None

    model_config = ConfigDict(
        extra="ignore",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    @field_validator("code", mode="before")
    @classmethod
    def _normalize_code(cls, value: Any) -> str:
        return _normalize_lang_code(value)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name must be a non-empty string")
        return cleaned

    @field_validator("build_strategy", mode="before")
    @classmethod
    def _normalize_build_strategy(cls, value: Any) -> str:
        return _clean_optional_str(value) or "fast"

    @field_validator("family", "last_build_time", "error_log", mode="before")
    @classmethod
    def _normalize_optional_text(cls, value: Any) -> Optional[str]:
        return _clean_optional_str(value)


class LexiconEntry(BaseModel):
    key: Optional[str] = None
    lemma: str
    pos: str
    language: str
    forms: dict[str, str] = Field(default_factory=dict)
    sense: Optional[str] = None
    wikidata_qid: Optional[str] = None
    source: Optional[str] = None
    confidence: float = 1.0
    meta: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    @field_validator("lemma", "pos", mode="before")
    @classmethod
    def _normalize_required_text(cls, value: Any) -> str:
        cleaned = _clean_optional_str(value)
        if not cleaned:
            raise ValueError("field must be a non-empty string")
        return cleaned

    @field_validator("language", mode="before")
    @classmethod
    def _normalize_entry_language(cls, value: Any) -> str:
        return _normalize_lang_code(value)

    @field_validator("forms", "meta", mode="before")
    @classmethod
    def _normalize_dict_fields(cls, value: Any) -> dict[str, Any]:
        return _coerce_mapping(value)

    @field_validator("sense", "wikidata_qid", "source", "key", mode="before")
    @classmethod
    def _normalize_optional_fields(cls, value: Any) -> Optional[str]:
        return _clean_optional_str(value)

    @field_validator("confidence", mode="before")
    @classmethod
    def _normalize_confidence(cls, value: Any) -> float:
        if value is None:
            return 1.0
        try:
            return float(value)
        except Exception:
            return 1.0


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------


class GenerationRequest(BaseModel):
    semantic_frame: Frame
    target_language: str

    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True,
        str_strip_whitespace=True,
        populate_by_name=True,
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_request_payload(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        raw = dict(data)

        semantic_frame = (
            raw.get("semantic_frame")
            or raw.get("frame")
            or raw.get("semanticFrame")
        )
        if semantic_frame is not None:
            raw["semantic_frame"] = semantic_frame

        lang = (
            raw.get("target_language")
            or raw.get("lang_code")
            or raw.get("lang")
            or raw.get("language")
        )

        inputs = raw.get("inputs")
        if lang is None and isinstance(inputs, dict):
            lang = (
                inputs.get("target_language")
                or inputs.get("lang_code")
                or inputs.get("lang")
                or inputs.get("language")
            )

        raw["target_language"] = lang
        return raw

    @field_validator("target_language", mode="before")
    @classmethod
    def _normalize_target_language(cls, value: Any) -> str:
        return _normalize_lang_code(value)

    @property
    def lang_code(self) -> str:
        return self.target_language


__all__ = [
    "Style",
    "SurfaceResult",
    "Sentence",
    "BaseFrame",
    "Frame",
    "BioFrame",
    "EventFrame",
    "RelationalFrame",
    "LanguageStatus",
    "GrammarType",
    "Language",
    "LexiconEntry",
    "GenerationRequest",
]