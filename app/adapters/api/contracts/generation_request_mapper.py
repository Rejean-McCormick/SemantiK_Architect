from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Union

import structlog

from app.adapters.ninai import ninai_adapter
from app.core.domain.exceptions import InvalidFrameError
from app.core.domain.frame import BioFrame
from app.core.domain.models import Frame
from app.shared.lexicon import lexicon

logger = structlog.get_logger()

_BIOISH_FRAME_TYPES = {
    "bio",
    "biography",
    "entity.person",
    "entity_person",
    "person",
    "entity.person.v1",
    "entity.person.v2",
}

_TOP_LEVEL_LANG_KEYS = ("lang", "language", "lang_code", "lang_name")
_INPUTS_LANG_KEYS = ("lang", "language", "lang_code")


@dataclass(frozen=True, slots=True)
class MappedGenerationRequest:
    """
    HTTP-to-domain generation request envelope.

    The router can depend on this mapper to:
    - resolve the authoritative language code,
    - strip transport-only language fields from the payload,
    - normalize bio/person payload variants,
    - parse Ninai or standard frame payloads into domain objects,
    - stop compatibility handling at the HTTP normalization boundary.
    """

    lang_code: str
    frame: Union[BioFrame, Frame]
    payload: Dict[str, Any]


def map_generation_request(
    payload: Mapping[str, Any],
    *,
    path_lang_code: Optional[str] = None,
) -> MappedGenerationRequest:
    """
    Convert an API payload into a normalized generation command.

    Rules:
    - If `path_lang_code` is provided, it is authoritative.
    - If both URL and payload languages are provided, they must match after normalization.
    - If no URL language is provided, the payload must contain one.
    - HTTP compatibility handling ends here; downstream runtime code receives
      only canonicalized domain objects plus cleaned payload data.
    """
    if not isinstance(payload, Mapping):
        raise InvalidFrameError("Payload must be a JSON object.")

    raw_payload = dict(payload)
    payload_lang_raw = extract_lang_from_payload(raw_payload)

    if path_lang_code:
        lang_code = normalize_lang_code(path_lang_code)

        if payload_lang_raw:
            payload_lang = normalize_lang_code(payload_lang_raw)
            if payload_lang != lang_code:
                raise InvalidFrameError(
                    f"Language mismatch: URL has '{path_lang_code}' -> '{lang_code}', "
                    f"payload has '{payload_lang_raw}' -> '{payload_lang}'."
                )
    else:
        if not payload_lang_raw:
            raise InvalidFrameError(
                "Missing language. Provide `lang` (top-level) or `inputs.language`."
            )
        lang_code = normalize_lang_code(payload_lang_raw)

    cleaned_payload = strip_lang_fields(raw_payload)
    frame = parse_generation_payload(cleaned_payload, lang_code)
    normalized_payload = canonicalize_clean_payload(cleaned_payload, frame)

    return MappedGenerationRequest(
        lang_code=lang_code,
        frame=frame,
        payload=normalized_payload,
    )


def normalize_lang_code(lang_code: str) -> str:
    """
    Normalize common language-code variants without assuming a fixed width.

    Current behavior:
    - trims and lowercases,
    - strips a leading `wiki` prefix if present,
    - delegates canonicalization to `lexicon.normalize_code`.
    """
    code = (lang_code or "").strip().lower()
    if code.startswith("wiki") and len(code) > 4:
        code = code[4:]

    normalized = (lexicon.normalize_code(code) or "").strip().lower()
    if not normalized:
        raise InvalidFrameError("Language code must be a non-empty string.")
    return normalized


def extract_lang_from_payload(payload: Mapping[str, Any]) -> Optional[str]:
    if not isinstance(payload, Mapping):
        return None

    for key in _TOP_LEVEL_LANG_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    inputs = payload.get("inputs")
    if isinstance(inputs, Mapping):
        for key in _INPUTS_LANG_KEYS:
            value = inputs.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    return None


def strip_lang_fields(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Remove transport-level language keys so they do not leak into frame parsing.
    """
    if not isinstance(payload, Mapping):
        raise InvalidFrameError("Payload must be a JSON object.")

    cleaned = dict(payload)

    for key in _TOP_LEVEL_LANG_KEYS:
        cleaned.pop(key, None)

    inputs = cleaned.get("inputs")
    if isinstance(inputs, Mapping):
        new_inputs = dict(inputs)
        for key in _INPUTS_LANG_KEYS:
            new_inputs.pop(key, None)
        cleaned["inputs"] = new_inputs

    return cleaned


def parse_generation_payload(
    payload: Mapping[str, Any], lang_code: str
) -> Union[BioFrame, Frame]:
    """
    Parse a normalized request payload into the domain frame expected by GenerateText.
    """
    if not isinstance(payload, Mapping):
        raise InvalidFrameError("Payload must be a JSON object.")

    payload_dict = dict(payload)

    if "function" in payload_dict:
        logger.info("ninai_protocol_detected", lang=lang_code)
        try:
            return ninai_adapter.parse(payload_dict)
        except ValueError as exc:
            raise InvalidFrameError(f"Ninai Parsing Error: {str(exc)}") from exc

    frame_type_raw = payload_dict.get("frame_type") or payload_dict.get("type")
    frame_type = str(frame_type_raw or "").strip()

    try:
        if is_bioish_frame_type(frame_type) or looks_like_bioish_payload(payload_dict):
            normalized = coerce_bio_payload(payload_dict)
            logger.info(
                "bio_payload_normalized",
                lang=lang_code,
                original_frame_type=frame_type or "(implicit_bio)",
                subject_keys=sorted(normalized["subject"].keys()),
            )
            return BioFrame(**normalized)

        if not frame_type:
            raise InvalidFrameError("Missing required field: frame_type")

        canonical_payload = dict(payload_dict)
        canonical_payload.pop("type", None)
        canonical_payload["frame_type"] = frame_type
        return Frame(**canonical_payload)
    except InvalidFrameError:
        raise
    except Exception as exc:
        raise InvalidFrameError(f"Invalid Frame format: {str(exc)}") from exc


def canonicalize_clean_payload(
    payload: Mapping[str, Any],
    frame: Union[BioFrame, Frame],
) -> Dict[str, Any]:
    """
    Return a stable cleaned payload view that matches the normalized domain frame.

    This is useful for router logging, downstream debug, and tests, while keeping
    HTTP compatibility handling out of the runtime layer.
    """
    if isinstance(frame, BioFrame):
        subject = dict(getattr(frame, "subject", {}) or {})
        return {
            "frame_type": "bio",
            "subject": subject,
            "context_id": getattr(frame, "context_id", "") or "",
            "meta": dict(getattr(frame, "meta", {}) or {}),
        }

    frame_payload = dict(payload)
    frame_payload.pop("type", None)
    frame_payload["frame_type"] = getattr(frame, "frame_type", None) or frame_payload.get(
        "frame_type", ""
    )
    return frame_payload


def is_bioish_frame_type(frame_type: Any) -> bool:
    ft = str(frame_type or "").strip().lower()
    return ft in _BIOISH_FRAME_TYPES or (ft.startswith("entity.") and "person" in ft)


def looks_like_bioish_payload(payload: Mapping[str, Any]) -> bool:
    """
    Heuristic for GUI/test-bench person payloads that omit an explicit bio frame_type.
    """
    if not isinstance(payload, Mapping):
        return False

    if is_bioish_frame_type(payload.get("frame_type") or payload.get("type")):
        return True

    subject = _merged_subject_payload(payload)
    return any(
        is_non_empty_scalar(subject.get(key))
        for key in (
            "name",
            "label",
            "profession",
            "occupation",
            "nationality",
            "citizenship",
            "gender",
            "sex",
            "qid",
        )
    )


def coerce_bio_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Accept both canonical BioFrame payloads and flat GUI/test-bench person payloads.

    Supported inputs:
      - canonical:
          {"frame_type": "bio", "subject": {"name": "Alan Turing", ...}}
      - flat:
          {"frame_type": "entity.person", "name": "Alan Turing", ...}
      - mixed:
          {"frame_type": "bio", "subject": {"name": "Alan Turing"}, "profession": "Mathematician"}
      - inputs-wrapped:
          {"frame_type": "entity.person", "inputs": {"name": "Alan Turing", ...}}
      - legacy-ish:
          {
            "frame_type": "bio",
            "main_entity": {"name": "Alan Turing", "id": "Q7251"},
            "primary_profession_lemmas": ["mathematician"],
            "nationality_lemmas": ["british"]
          }

    Output is the canonical BioFrame payload shape expected by the runtime:
      {
        "frame_type": "bio",
        "subject": {...},
        "context_id": "...",
        "meta": {...}
      }
    """
    if not isinstance(payload, Mapping):
        raise InvalidFrameError("Payload must be a JSON object.")

    merged = _merged_subject_payload(payload)

    name = _pick_scalar(merged, "name", "label")
    profession = _pick_scalar(merged, "profession", "occupation")
    nationality = _pick_scalar(merged, "nationality", "citizenship")
    gender = _pick_scalar(merged, "gender", "sex")
    qid = _pick_scalar(merged, "qid", "id", "entity_id")

    if not is_non_empty_scalar(name):
        raise InvalidFrameError(
            "Bio/person payload requires a subject name. "
            "Provide `subject.name` or top-level `name`/`label`."
        )

    subject: Dict[str, Any] = {"name": str(name).strip()}

    if is_non_empty_scalar(qid):
        subject["qid"] = str(qid).strip()
    if is_non_empty_scalar(profession):
        subject["profession"] = str(profession).strip()
    if is_non_empty_scalar(nationality):
        subject["nationality"] = str(nationality).strip()
    if is_non_empty_scalar(gender):
        subject["gender"] = str(gender).strip()

    context_id = _pick_scalar(payload, "context_id")
    if not is_non_empty_scalar(context_id):
        context_id = qid

    meta = payload.get("meta")
    if isinstance(meta, Mapping):
        canonical_meta: Dict[str, Any] = dict(meta)
    else:
        canonical_meta = {}

    return {
        "frame_type": "bio",
        "subject": subject,
        "context_id": str(context_id).strip() if is_non_empty_scalar(context_id) else "",
        "meta": canonical_meta,
    }


def _merged_subject_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Merge supported person/bio payload variants into one subject-like mapping
    without mutating the original payload.
    """
    merged: Dict[str, Any] = {}

    inputs = payload.get("inputs")
    if isinstance(inputs, Mapping):
        inputs_subject = inputs.get("subject")
        if isinstance(inputs_subject, Mapping):
            merged.update(dict(inputs_subject))

    raw_subject = payload.get("subject")
    if isinstance(raw_subject, Mapping):
        merged.update(dict(raw_subject))

    main_entity = payload.get("main_entity")
    if isinstance(main_entity, Mapping):
        merged.update(dict(main_entity))

    properties = payload.get("properties")
    if isinstance(properties, Mapping):
        for key in (
            "name",
            "label",
            "profession",
            "occupation",
            "nationality",
            "citizenship",
            "gender",
            "sex",
            "qid",
        ):
            value = properties.get(key)
            if is_non_empty_scalar(value) and not is_non_empty_scalar(merged.get(key)):
                merged[key] = value

    for source in (inputs, payload):
        if not isinstance(source, Mapping):
            continue

        _copy_first_scalar(source, merged, "name", "name")
        _copy_first_scalar(source, merged, "label", "name")
        _copy_first_scalar(source, merged, "name", "label")
        _copy_first_scalar(source, merged, "profession", "profession")
        _copy_first_scalar(source, merged, "occupation", "profession")
        _copy_first_scalar(source, merged, "nationality", "nationality")
        _copy_first_scalar(source, merged, "citizenship", "nationality")
        _copy_first_scalar(source, merged, "gender", "gender")
        _copy_first_scalar(source, merged, "sex", "gender")
        _copy_first_scalar(source, merged, "qid", "qid")

    prof_lemmas = payload.get("primary_profession_lemmas")
    if isinstance(prof_lemmas, list) and prof_lemmas and not is_non_empty_scalar(
        merged.get("profession")
    ):
        first_prof = _first_non_empty_scalar(prof_lemmas)
        if first_prof is not None:
            merged["profession"] = first_prof

    nat_lemmas = payload.get("nationality_lemmas")
    if isinstance(nat_lemmas, list) and nat_lemmas and not is_non_empty_scalar(
        merged.get("nationality")
    ):
        first_nat = _first_non_empty_scalar(nat_lemmas)
        if first_nat is not None:
            merged["nationality"] = first_nat

    return merged


def _copy_first_scalar(
    source: Mapping[str, Any],
    target: Dict[str, Any],
    source_key: str,
    target_key: str,
) -> None:
    value = source.get(source_key)
    if is_non_empty_scalar(value) and not is_non_empty_scalar(target.get(target_key)):
        target[target_key] = value


def _pick_scalar(source: Mapping[str, Any], *keys: str) -> Optional[Any]:
    for key in keys:
        value = source.get(key)
        if is_non_empty_scalar(value):
            return value
    return None


def _first_non_empty_scalar(values: list[Any]) -> Optional[Any]:
    for value in values:
        if is_non_empty_scalar(value):
            return value
    return None


def is_non_empty_scalar(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


__all__ = [
    "MappedGenerationRequest",
    "map_generation_request",
    "normalize_lang_code",
    "extract_lang_from_payload",
    "strip_lang_fields",
    "parse_generation_payload",
    "canonicalize_clean_payload",
    "is_bioish_frame_type",
    "looks_like_bioish_payload",
    "coerce_bio_payload",
]