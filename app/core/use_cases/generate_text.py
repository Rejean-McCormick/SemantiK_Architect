```python
# app/core/use_cases/generate_text.py
from __future__ import annotations

import inspect
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import structlog

from app.core.domain.exceptions import DomainError, InvalidFrameError
from app.core.domain.models import Frame, Sentence, SurfaceResult
from app.core.ports.grammar_engine import IGrammarEngine
from app.core.ports.llm_port import ILanguageModel
from app.shared.observability import get_tracer

logger = structlog.get_logger()
tracer = get_tracer(__name__)

PLANNER_FIRST_RUNTIME_PATH = "planner_first"
LEGACY_ENGINE_FALLBACK_RUNTIME_PATH = "legacy_engine_fallback"

LEGACY_FALLBACK_REASON_PLANNER_UNAVAILABLE = "planner_runtime_unavailable"
LEGACY_FALLBACK_REASON_PLANNER_FAILED = "planner_runtime_failed"

LEGACY_RENDERER_BACKEND = "gf"
DEFAULT_COMPATIBILITY_CONSTRUCTION_ID = "copula_equative_classification"

_CANONICAL_DEBUG_KEYS = (
    "runtime_path",
    "construction_id",
    "renderer_backend",
    "lang_code",
    "fallback_used",
    "slot_keys",
)


@dataclass(frozen=True, slots=True)
class _FallbackSurfaceResult:
    text: str
    lang_code: str
    construction_id: str
    renderer_backend: str
    fallback_used: bool
    tokens: list[str] = field(default_factory=list)
    debug_info: dict[str, Any] = field(default_factory=dict)
    generation_time_ms: float = 0.0


def _build_surface_result(
    *,
    text: str,
    lang_code: str,
    construction_id: str,
    renderer_backend: str,
    fallback_used: bool,
    tokens: list[str],
    debug_info: dict[str, Any],
    generation_time_ms: float,
) -> Any:
    """
    Construct the canonical SurfaceResult if available.

    During migration, `Sentence` may still behave as a compatibility alias/model
    around the same canonical runtime fields. We prefer SurfaceResult first.
    """
    for result_type in (SurfaceResult, Sentence):
        try:
            return result_type(
                text=text,
                lang_code=lang_code,
                construction_id=construction_id,
                renderer_backend=renderer_backend,
                fallback_used=fallback_used,
                tokens=tokens,
                debug_info=debug_info,
                generation_time_ms=generation_time_ms,
            )
        except TypeError:
            continue

    return _FallbackSurfaceResult(
        text=text,
        lang_code=lang_code,
        construction_id=construction_id,
        renderer_backend=renderer_backend,
        fallback_used=fallback_used,
        tokens=tokens,
        debug_info=debug_info,
        generation_time_ms=generation_time_ms,
    )


class GenerateText:
    """
    Public application use case for single-sentence generation.

    Runtime policy:
    - Nominal path: planner-first runtime
        frame -> planner -> lexical resolution -> realizer -> SurfaceResult
    - Legacy path: compatibility fallback only
        frame -> engine.generate(...) -> SurfaceResult

    Important invariants:
    - The legacy engine is never the nominal/default runtime path.
    - If legacy is used, it is always explicit and visible in debug_info.
    - Planner-first results must carry enough runtime metadata to support
      the public response contract and downstream observability.
    - The response mapper serializes runtime truth; it must not become the
      first place where nominal planner-first metadata becomes real.
    - On nominal planner-first success, the runtime result must already expose
      top-level `construction_id`, `renderer_backend`, `fallback_used`,
      `tokens`, and `generation_time_ms`.
    """

    def __init__(
        self,
        engine: Optional[IGrammarEngine] = None,
        llm: Optional[ILanguageModel] = None,
        *,
        planner: Any | None = None,
        lexical_resolver: Any | None = None,
        realizer: Any | None = None,
        allow_legacy_engine_fallback: bool = True,
    ) -> None:
        # Legacy compatibility dependency
        self.engine = engine

        # Optional post-processing dependency (not used by default)
        self.llm = llm

        # Planner-first runtime dependencies
        self.planner = planner
        self.lexical_resolver = lexical_resolver
        self.realizer = realizer

        # Migration control
        self.allow_legacy_engine_fallback = allow_legacy_engine_fallback

    async def execute(self, lang_code: str, frame: Frame) -> SurfaceResult:
        """
        Generate a single SurfaceResult from a semantic Frame.

        Args:
            lang_code:
                Target language code.
            frame:
                Semantic/domain frame.

        Returns:
            SurfaceResult:
                Canonical runtime result, mapper-ready on the nominal path.

        Raises:
            InvalidFrameError:
                When the input frame is structurally invalid.
            DomainError:
                When generation fails or the use case is misconfigured.
        """
        started = time.perf_counter()

        with tracer.start_as_current_span("use_case.generate_text") as span:
            frame_type = str(getattr(frame, "frame_type", "unknown") or "unknown")
            normalized_lang_code = self._normalize_lang_code(lang_code)

            span.set_attribute("app.lang_code", normalized_lang_code)
            span.set_attribute("app.frame_type", frame_type)

            logger.info(
                "generation_started",
                lang=normalized_lang_code,
                frame_type=frame_type,
                planner_runtime_configured=self._planner_runtime_available(),
                legacy_engine_configured=self.engine is not None,
            )

            try:
                self._validate_lang_code(normalized_lang_code)
                self._validate_frame(frame)

                if self._planner_runtime_available():
                    try:
                        result = await self._generate_via_planner_runtime(
                            lang_code=normalized_lang_code,
                            frame=frame,
                        )
                        runtime_path = PLANNER_FIRST_RUNTIME_PATH
                    except InvalidFrameError:
                        raise
                    except Exception as planner_exc:
                        if not self._can_fallback_to_legacy_engine():
                            raise

                        logger.warning(
                            "planner_runtime_failed_falling_back",
                            lang=normalized_lang_code,
                            frame_type=frame_type,
                            error=str(planner_exc),
                            planner=self._component_name(self.planner),
                            lexical_resolver=self._component_name(self.lexical_resolver),
                            realizer=self._component_name(self.realizer),
                        )

                        result = await self._generate_via_legacy_engine(
                            lang_code=normalized_lang_code,
                            frame=frame,
                            fallback_reason=f"{LEGACY_FALLBACK_REASON_PLANNER_FAILED}: {planner_exc}",
                        )
                        runtime_path = LEGACY_ENGINE_FALLBACK_RUNTIME_PATH
                else:
                    if not self._can_fallback_to_legacy_engine():
                        raise DomainError(
                            "Planner-first runtime is required but not configured, "
                            "and legacy fallback is disabled."
                        )

                    logger.warning(
                        "planner_runtime_unavailable_using_explicit_legacy_fallback",
                        lang=normalized_lang_code,
                        frame_type=frame_type,
                        planner=self._component_name(self.planner),
                        lexical_resolver=self._component_name(self.lexical_resolver),
                        realizer=self._component_name(self.realizer),
                        legacy_engine=self._component_name(self.engine),
                    )

                    result = await self._generate_via_legacy_engine(
                        lang_code=normalized_lang_code,
                        frame=frame,
                        fallback_reason=LEGACY_FALLBACK_REASON_PLANNER_UNAVAILABLE,
                    )
                    runtime_path = LEGACY_ENGINE_FALLBACK_RUNTIME_PATH

                result = self._finalize_surface_result(
                    result=result,
                    lang_code=normalized_lang_code,
                    frame=frame,
                    elapsed_ms=(time.perf_counter() - started) * 1000.0,
                    runtime_path=runtime_path,
                )

                span.set_attribute("app.runtime_path", runtime_path)
                span.set_attribute("app.generated_length", len(result.text))
                span.set_attribute("app.fallback_used", bool(result.fallback_used))
                span.set_attribute("app.construction_id", str(result.construction_id))
                span.set_attribute("app.renderer_backend", str(result.renderer_backend))

                logger.info(
                    "generation_success",
                    lang=result.lang_code,
                    runtime_path=runtime_path,
                    text_preview=result.text[:80],
                    construction_id=result.construction_id,
                    renderer_backend=result.renderer_backend,
                    fallback_used=result.fallback_used,
                )

                return result

            except DomainError:
                raise
            except Exception as exc:
                logger.error(
                    "generation_failed",
                    lang=normalized_lang_code,
                    frame_type=frame_type,
                    error=str(exc),
                    exc_info=True,
                )
                raise DomainError(f"Unexpected generation failure: {str(exc)}") from exc

    async def _generate_via_planner_runtime(
        self,
        *,
        lang_code: str,
        frame: Frame,
    ) -> SurfaceResult:
        """
        Run the planner-first runtime.

        Migration-tolerant behavior:
        - planner output may be a single object or a sequence,
        - lexical resolver is optional,
        - realizer is authoritative for the final surface result.

        Planner-first is the only nominal runtime path. If its returned
        metadata is too weak for the public contract, the result is rejected
        here so the caller can explicitly fall back or fail fast.
        """
        planned = await self._call_planner(lang_code=lang_code, frame=frame)
        runtime_payload = planned

        if self.lexical_resolver is not None:
            runtime_payload = await self._call_lexical_resolver(
                payload=runtime_payload,
                lang_code=lang_code,
                frame=frame,
            )

        realized = await self._call_realizer(
            payload=runtime_payload,
            lang_code=lang_code,
            frame=frame,
        )

        construction_id = self._extract_canonical_construction_id(
            value=realized,
            fallback_payload=runtime_payload,
            frame=frame,
        )

        slot_keys = self._extract_slot_keys(runtime_payload)
        debug_info: dict[str, Any] = {
            "runtime_path": PLANNER_FIRST_RUNTIME_PATH,
            "fallback_used": False,
            "planner": self._component_name(self.planner),
            "lexical_resolver": self._component_name(self.lexical_resolver),
            "realizer": self._component_name(self.realizer),
            "lang_code": self._normalize_lang_code(lang_code),
            "construction_id": construction_id,
            "slot_keys": slot_keys,
        }

        result = self._coerce_to_surface_result(
            value=realized,
            lang_code=lang_code,
            default_debug_info=debug_info,
            default_construction_id=construction_id,
            default_renderer_backend=None,
        )

        return self._enforce_planner_runtime_metadata(result)

    async def _generate_via_legacy_engine(
        self,
        *,
        lang_code: str,
        frame: Frame,
        fallback_reason: str,
    ) -> SurfaceResult:
        """
        Run the legacy direct frame-to-engine path as an explicit fallback only.
        """
        if self.engine is None:
            raise DomainError("Legacy grammar engine fallback is not configured.")

        result = await self.engine.generate(lang_code, frame)
        construction_id = self._infer_construction_id_from_frame(frame)

        debug_info = {
            "runtime_path": LEGACY_ENGINE_FALLBACK_RUNTIME_PATH,
            "fallback_used": True,
            "fallback_reason": fallback_reason,
            "legacy_engine": self._component_name(self.engine),
            "planner_runtime_configured": self._planner_runtime_available(),
            "renderer_backend": LEGACY_RENDERER_BACKEND,
            "selected_backend": LEGACY_RENDERER_BACKEND,
            "attempted_backends": [LEGACY_RENDERER_BACKEND],
            "lang_code": self._normalize_lang_code(lang_code),
            "construction_id": construction_id,
            "slot_keys": self._infer_slot_keys_from_frame(frame),
        }

        return self._coerce_to_surface_result(
            value=result,
            lang_code=lang_code,
            default_debug_info=debug_info,
            default_construction_id=construction_id,
            default_renderer_backend=LEGACY_RENDERER_BACKEND,
        )

    async def _call_planner(self, *, lang_code: str, frame: Frame) -> Any:
        if self.planner is None:
            raise DomainError("Planner runtime is not configured.")

        attempts = [
            (((frame,),), {"lang_code": lang_code}),
            (((frame,),), {"lang_code": lang_code, "domain": "auto"}),
            ((frame,), {"lang_code": lang_code}),
            (((frame,),), {}),
            ((frame,), {}),
        ]

        result = await self._call_method_attempts(self.planner, "plan", attempts)
        return self._normalize_single_sentence_payload(result, stage="planner")

    async def _call_lexical_resolver(
        self,
        *,
        payload: Any,
        lang_code: str,
        frame: Frame,
    ) -> Any:
        resolver = self.lexical_resolver
        if resolver is None:
            return payload

        attempts = [
            ((payload,), {"lang_code": lang_code, "frame": frame}),
            ((payload,), {"lang_code": lang_code}),
            ((payload,), {}),
        ]

        return await self._call_method_attempts(resolver, "resolve", attempts)

    async def _call_realizer(
        self,
        *,
        payload: Any,
        lang_code: str,
        frame: Frame,
    ) -> Any:
        if self.realizer is None:
            raise DomainError("Planner runtime is missing a realizer.")

        attempts = [
            ((payload,), {"lang_code": lang_code, "frame": frame}),
            ((payload,), {"lang_code": lang_code}),
            ((payload,), {}),
        ]

        return await self._call_method_attempts(self.realizer, "realize", attempts)

    async def _call_method_attempts(
        self,
        target: Any,
        method_name: str,
        attempts: list[tuple[tuple[Any, ...], dict[str, Any]]],
    ) -> Any:
        """
        Attempt a method call across a small set of migration-safe signatures.
        """
        method = getattr(target, method_name, None)
        if method is None:
            raise DomainError(
                f"{self._component_name(target)} does not implement '{method_name}()'."
            )

        last_type_error: TypeError | None = None

        for args, kwargs in attempts:
            try:
                value = method(*args, **kwargs)
                if inspect.isawaitable(value):
                    value = await value
                return value
            except TypeError as exc:
                last_type_error = exc
                continue

        raise DomainError(
            f"{self._component_name(target)}.{method_name}() could not be called "
            f"with any supported migration signature."
        ) from last_type_error

    def _normalize_single_sentence_payload(self, value: Any, *, stage: str) -> Any:
        """
        Normalize planner-like outputs to the single-sentence runtime payload.
        """
        if value is None:
            raise DomainError(f"{stage.capitalize()} returned no result.")

        if isinstance(value, (str, bytes, bytearray, dict, SurfaceResult, Sentence)):
            return value

        if isinstance(value, (list, tuple)):
            if not value:
                raise DomainError(f"{stage.capitalize()} returned an empty sequence.")
            return value[0]

        return value

    def _coerce_to_surface_result(
        self,
        *,
        value: Any,
        lang_code: str,
        default_debug_info: dict[str, Any],
        default_construction_id: str | None,
        default_renderer_backend: str | None,
    ) -> SurfaceResult:
        """
        Convert a planner/realizer/engine result into the canonical runtime result.
        """
        normalized_lang_code = self._normalize_lang_code(lang_code)
        default_debug = dict(default_debug_info)

        if isinstance(value, str):
            text = value
            current_debug = {}
            raw_lang = normalized_lang_code
            construction_id = default_construction_id
            renderer_backend = default_renderer_backend
            fallback_used = self._coerce_bool(default_debug.get("fallback_used"), default=False)
            tokens = []
            generation_time_ms = 0.0
        else:
            text = self._extract_text(value)
            current_debug = self._coerce_debug_info(self._get_value(value, "debug_info", {}))
            raw_lang = self._get_value(value, "lang_code", None) or self._get_value(
                value, "language", normalized_lang_code
            )

            construction_id = self._extract_canonical_construction_id(
                value=value,
                fallback_payload=None,
                frame=None,
                default_value=default_construction_id,
                debug_info=current_debug,
            )

            renderer_backend = self._first_non_empty_string(
                self._get_value(value, "renderer_backend", None),
                current_debug.get("renderer_backend"),
                default_renderer_backend,
                default_debug.get("renderer_backend"),
            )

            fallback_used = self._coerce_bool(
                self._first_not_none(
                    self._get_value(value, "fallback_used", None),
                    current_debug.get("fallback_used"),
                    default_debug.get("fallback_used"),
                ),
                default=False,
            )

            tokens = self._coerce_tokens(
                self._first_not_none(
                    self._get_value(value, "tokens", None),
                    current_debug.get("tokens"),
                    default_debug.get("tokens"),
                )
            )

            generation_time_ms = self._coerce_float(
                self._first_not_none(
                    self._get_value(value, "generation_time_ms", None),
                    current_debug.get("generation_time_ms"),
                    default_debug.get("generation_time_ms"),
                ),
                default=0.0,
            )

        if text is None:
            raise DomainError(
                f"Cannot map result of type '{type(value).__name__}' into SurfaceResult: "
                "missing 'text'."
            )

        merged_debug = self._merge_debug_info(current_debug, default_debug)
        normalized_result_lang = self._normalize_lang_code(raw_lang or normalized_lang_code)

        if not tokens:
            tokens = self._default_tokens(str(text))

        if not self._is_non_empty_string(renderer_backend):
            renderer_backend = self._first_non_empty_string(
                merged_debug.get("renderer_backend"),
                default_renderer_backend,
            )

        if not self._is_non_empty_string(construction_id):
            construction_id = self._first_non_empty_string(
                merged_debug.get("construction_id"),
                default_construction_id,
            )

        merged_debug["lang_code"] = normalized_result_lang
        merged_debug["fallback_used"] = fallback_used
        merged_debug["tokens"] = list(tokens)
        merged_debug.setdefault("slot_keys", self._coerce_slot_keys(merged_debug.get("slot_keys")))

        if self._is_non_empty_string(construction_id):
            merged_debug["construction_id"] = str(construction_id)
        if self._is_non_empty_string(renderer_backend):
            merged_debug["renderer_backend"] = str(renderer_backend)

        return _build_surface_result(
            text=str(text).strip(),
            lang_code=normalized_result_lang,
            construction_id=str(construction_id or ""),
            renderer_backend=str(renderer_backend or ""),
            fallback_used=fallback_used,
            tokens=list(tokens),
            debug_info=merged_debug,
            generation_time_ms=generation_time_ms,
        )

    def _enforce_planner_runtime_metadata(self, result: SurfaceResult) -> SurfaceResult:
        """
        Planner-first results must provide enough top-level metadata to support
        the public response contract and observability.
        """
        missing: list[str] = []

        if not self._is_non_empty_string(getattr(result, "construction_id", None)):
            missing.append("construction_id")
        if not self._is_non_empty_string(getattr(result, "renderer_backend", None)):
            missing.append("renderer_backend")

        tokens = self._coerce_tokens(getattr(result, "tokens", None))
        if not tokens:
            missing.append("tokens")

        debug_info = self._coerce_debug_info(getattr(result, "debug_info", None))
        if not isinstance(debug_info, dict):
            missing.append("debug_info")

        if missing:
            raise DomainError(
                "Planner-first generation returned an incomplete runtime result: "
                f"missing {', '.join(missing)}."
            )

        debug_info["runtime_path"] = PLANNER_FIRST_RUNTIME_PATH
        debug_info["construction_id"] = str(result.construction_id)
        debug_info["renderer_backend"] = str(result.renderer_backend)
        debug_info["lang_code"] = self._normalize_lang_code(result.lang_code)
        debug_info["fallback_used"] = self._coerce_bool(result.fallback_used, default=False)
        debug_info["tokens"] = list(tokens)
        debug_info.setdefault("slot_keys", self._coerce_slot_keys(debug_info.get("slot_keys")))

        generation_time_ms = self._coerce_float(
            getattr(result, "generation_time_ms", 0.0),
            default=0.0,
        )

        return _build_surface_result(
            text=str(result.text).strip(),
            lang_code=self._normalize_lang_code(result.lang_code),
            construction_id=str(result.construction_id),
            renderer_backend=str(result.renderer_backend),
            fallback_used=self._coerce_bool(result.fallback_used, default=False),
            tokens=list(tokens),
            debug_info=debug_info,
            generation_time_ms=generation_time_ms,
        )

    def _finalize_surface_result(
        self,
        *,
        result: SurfaceResult,
        lang_code: str,
        frame: Frame,
        elapsed_ms: float,
        runtime_path: str,
    ) -> SurfaceResult:
        """
        Final cleanup to guarantee a stable canonical runtime result before
        public response mapping.
        """
        text = str(getattr(result, "text", "") or "").strip()
        normalized_lang_code = self._normalize_lang_code(
            getattr(result, "lang_code", None) or lang_code
        )
        construction_id = self._first_non_empty_string(
            getattr(result, "construction_id", None),
            self._infer_construction_id_from_frame(frame),
        )
        renderer_backend = self._first_non_empty_string(
            getattr(result, "renderer_backend", None),
            LEGACY_RENDERER_BACKEND if runtime_path != PLANNER_FIRST_RUNTIME_PATH else None,
        )

        if not self._is_non_empty_string(text):
            raise DomainError("Generation produced empty text.")

        if not self._is_non_empty_string(construction_id):
            raise DomainError("Runtime result is missing required field 'construction_id'.")

        if not self._is_non_empty_string(renderer_backend):
            raise DomainError("Runtime result is missing required field 'renderer_backend'.")

        debug_info = self._coerce_debug_info(getattr(result, "debug_info", None))
        fallback_used = self._coerce_bool(getattr(result, "fallback_used", False), default=False)

        if runtime_path != PLANNER_FIRST_RUNTIME_PATH:
            fallback_used = True
            debug_info.setdefault("selected_backend", LEGACY_RENDERER_BACKEND)
            attempted_backends = debug_info.get("attempted_backends")
            if not isinstance(attempted_backends, list) or not attempted_backends:
                debug_info["attempted_backends"] = [LEGACY_RENDERER_BACKEND]
        else:
            # Planner-first remains the nominal runtime path, but internal backend
            # fallback may still have occurred and must stay visible.
            debug_info.setdefault("selected_backend", renderer_backend)

        tokens = self._coerce_tokens(getattr(result, "tokens", None))
        if not tokens:
            tokens = self._default_tokens(text)

        generation_time_ms = self._coerce_float(
            getattr(result, "generation_time_ms", 0.0),
            default=0.0,
        )
        if generation_time_ms <= 0.0:
            generation_time_ms = float(elapsed_ms)

        debug_info["runtime_path"] = runtime_path
        debug_info["lang_code"] = normalized_lang_code
        debug_info["construction_id"] = construction_id
        debug_info["renderer_backend"] = renderer_backend
        debug_info["fallback_used"] = fallback_used
        debug_info["tokens"] = list(tokens)
        debug_info["generation_time_ms"] = generation_time_ms
        debug_info["slot_keys"] = self._coerce_slot_keys(
            debug_info.get("slot_keys", self._infer_slot_keys_from_frame(frame))
        )

        return _build_surface_result(
            text=text,
            lang_code=normalized_lang_code,
            construction_id=construction_id,
            renderer_backend=renderer_backend,
            fallback_used=fallback_used,
            tokens=list(tokens),
            debug_info=debug_info,
            generation_time_ms=generation_time_ms,
        )

    def _validate_lang_code(self, lang_code: str) -> None:
        if not isinstance(lang_code, str) or not lang_code.strip():
            raise DomainError("lang_code must be a non-empty string.")

    def _validate_frame(self, frame: Frame) -> None:
        """
        Enforce semantic preconditions before generation.
        """
        if frame is None:
            raise InvalidFrameError("Frame is required.")

        frame_type = str(getattr(frame, "frame_type", "") or "").strip()
        if not frame_type:
            raise InvalidFrameError("Frame must have a 'frame_type'.")

        if self._looks_like_bio_or_person_frame(frame_type):
            subject = getattr(frame, "subject", None)

            if not subject:
                raise InvalidFrameError("Bio/person frame requires a 'subject'.")

            subject_name = self._extract_subject_name(subject)
            if not subject_name:
                direct_name = getattr(frame, "name", None)
                if not isinstance(direct_name, str) or not direct_name.strip():
                    raise InvalidFrameError(
                        "Bio/person frame subject must have a non-empty 'name' field."
                    )

    def _looks_like_bio_or_person_frame(self, frame_type: str) -> bool:
        normalized = frame_type.strip().lower()
        return (
            normalized == "bio"
            or normalized.startswith("bio")
            or "person" in normalized
            or normalized == "biography"
        )

    def _extract_subject_name(self, subject: Any) -> str | None:
        if isinstance(subject, dict):
            value = subject.get("name")
            return value.strip() if isinstance(value, str) and value.strip() else None

        value = getattr(subject, "name", None)
        return value.strip() if isinstance(value, str) and value.strip() else None

    def _planner_runtime_available(self) -> bool:
        return self.planner is not None and self.realizer is not None

    def _can_fallback_to_legacy_engine(self) -> bool:
        return self.allow_legacy_engine_fallback and self.engine is not None

    def _merge_debug_info(
        self,
        current: Any,
        defaults: dict[str, Any],
    ) -> dict[str, Any]:
        merged = dict(defaults)

        if isinstance(current, dict):
            merged.update(current)
        elif current is not None:
            merged["raw_debug_info"] = current

        for key in _CANONICAL_DEBUG_KEYS:
            if key not in merged:
                if key == "slot_keys":
                    merged[key] = []
                elif key == "fallback_used":
                    merged[key] = False
                elif key == "runtime_path":
                    merged[key] = "unknown"

        merged["slot_keys"] = self._coerce_slot_keys(merged.get("slot_keys"))
        merged["fallback_used"] = self._coerce_bool(merged.get("fallback_used"), default=False)
        return merged

    def _extract_text(self, value: Any) -> str | None:
        if isinstance(value, dict):
            text = value.get("text")
            if text is None and "surface_text" in value:
                text = value.get("surface_text")
            return str(text) if text is not None else None

        text = getattr(value, "text", None)
        return str(text) if text is not None else None

    def _extract_slot_keys(self, payload: Any) -> list[str]:
        slot_map = self._get_value(payload, "slot_map", None)
        if isinstance(slot_map, dict):
            return sorted(str(k) for k in slot_map.keys())
        return []

    def _extract_canonical_construction_id(
        self,
        *,
        value: Any,
        fallback_payload: Any | None,
        frame: Frame | None,
        default_value: str | None = None,
        debug_info: dict[str, Any] | None = None,
    ) -> str | None:
        debug_info = debug_info or {}
        return self._first_non_empty_string(
            self._get_value(value, "construction_id", None),
            self._get_value(fallback_payload, "construction_id", None) if fallback_payload is not None else None,
            debug_info.get("construction_id"),
            default_value,
            self._infer_construction_id_from_frame(frame) if frame is not None else None,
        )

    def _infer_construction_id_from_frame(self, frame: Frame | None) -> str | None:
        if frame is None:
            return None

        frame_type = str(getattr(frame, "frame_type", "") or "").strip().lower()
        if self._looks_like_bio_or_person_frame(frame_type):
            return DEFAULT_COMPATIBILITY_CONSTRUCTION_ID

        if "locative" in frame_type or "location" in frame_type:
            return "copula_locative"

        if "event" in frame_type:
            return "topic_comment_eventive"

        return None

    def _infer_slot_keys_from_frame(self, frame: Frame | None) -> list[str]:
        if frame is None:
            return []

        candidate_keys = (
            "subject",
            "profession",
            "nationality",
            "predicate_nominal",
            "predicate_adjective",
            "location",
            "event",
            "agent",
            "patient",
            "theme",
            "time",
            "topic",
            "comment",
            "name",
        )

        keys: list[str] = []
        for key in candidate_keys:
            value = getattr(frame, key, None)
            if value is not None:
                keys.append(key)

        return sorted(set(keys))

    def _coerce_debug_info(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return dict(value)
        if value is None:
            return {}
        return {"raw_debug_info": value}

    def _coerce_tokens(self, value: Any) -> list[str]:
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            return [str(item) for item in value]
        if isinstance(value, tuple) and all(isinstance(item, str) for item in value):
            return [str(item) for item in value]
        return []

    def _coerce_slot_keys(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value if isinstance(item, str)]
        if isinstance(value, tuple):
            return [str(item) for item in value if isinstance(item, str)]
        return []

    def _coerce_bool(self, value: Any, *, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "y"}:
                return True
            if normalized in {"false", "0", "no", "n"}:
                return False
        return bool(value)

    def _coerce_float(self, value: Any, *, default: float) -> float:
        try:
            if value is None:
                return float(default)
            return float(value)
        except Exception:
            return float(default)

    def _default_tokens(self, text: str) -> list[str]:
        return [part for part in str(text).split() if part]

    def _get_value(self, target: Any, key: str, default: Any = None) -> Any:
        if target is None:
            return default
        if isinstance(target, dict):
            return target.get(key, default)
        return getattr(target, key, default)

    def _normalize_lang_code(self, lang_code: Any) -> str:
        return str(lang_code or "").strip().lower()

    def _is_non_empty_string(self, value: Any) -> bool:
        return isinstance(value, str) and bool(value.strip())

    def _first_non_empty_string(self, *values: Any) -> str | None:
        for value in values:
            if self._is_non_empty_string(value):
                return str(value).strip()
        return None

    def _first_not_none(self, *values: Any) -> Any:
        for value in values:
            if value is not None:
                return value
        return None

    def _component_name(self, component: Any) -> str | None:
        if component is None:
            return None
        return component.__class__.__name__
```
