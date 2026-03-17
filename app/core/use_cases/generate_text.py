# app/core/use_cases/generate_text.py
from __future__ import annotations

import inspect
import time
from typing import Any, Optional

import structlog

from app.core.domain.exceptions import DomainError, InvalidFrameError
from app.core.domain.models import Frame, Sentence
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


class GenerateText:
    """
    Public application use case for single-sentence generation.

    Runtime policy:
    - Nominal path: planner-first runtime
        frame -> planner -> lexical resolution -> realizer -> Sentence
    - Legacy path: compatibility fallback only
        frame -> engine.generate(...) -> Sentence

    Important invariants:
    - The legacy engine is never the nominal/default runtime path.
    - If legacy is used, it is always explicit and visible in debug_info.
    - Planner-first results must carry enough runtime metadata to support
      the public response contract and downstream observability.
    - This use case remains tolerant of evolving planner/lexical/realizer
      call signatures during migration.
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

    async def execute(self, lang_code: str, frame: Frame) -> Sentence:
        """
        Generate a single Sentence from a semantic Frame.

        Args:
            lang_code:
                Target language code.
            frame:
                Semantic/domain frame.

        Returns:
            Sentence:
                Compatibility wrapper over the final surface result.

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
                        sentence = await self._generate_via_planner_runtime(
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

                        sentence = await self._generate_via_legacy_engine(
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

                    sentence = await self._generate_via_legacy_engine(
                        lang_code=normalized_lang_code,
                        frame=frame,
                        fallback_reason=LEGACY_FALLBACK_REASON_PLANNER_UNAVAILABLE,
                    )
                    runtime_path = LEGACY_ENGINE_FALLBACK_RUNTIME_PATH

                sentence = self._finalize_sentence(
                    sentence=sentence,
                    lang_code=normalized_lang_code,
                    elapsed_ms=(time.perf_counter() - started) * 1000.0,
                    runtime_path=runtime_path,
                )

                construction_id = (sentence.debug_info or {}).get("construction_id")
                renderer_backend = (sentence.debug_info or {}).get("renderer_backend")
                fallback_used = bool((sentence.debug_info or {}).get("fallback_used", False))

                span.set_attribute("app.runtime_path", runtime_path)
                span.set_attribute("app.generated_length", len(sentence.text))
                span.set_attribute("app.fallback_used", fallback_used)

                if construction_id:
                    span.set_attribute("app.construction_id", str(construction_id))
                if renderer_backend:
                    span.set_attribute("app.renderer_backend", str(renderer_backend))

                logger.info(
                    "generation_success",
                    lang=sentence.lang_code,
                    runtime_path=runtime_path,
                    text_preview=sentence.text[:80],
                    construction_id=construction_id,
                    renderer_backend=renderer_backend,
                    fallback_used=fallback_used,
                )

                return sentence

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
    ) -> Sentence:
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

        debug_info: dict[str, Any] = {
            "runtime_path": PLANNER_FIRST_RUNTIME_PATH,
            "fallback_used": False,
            "planner": self._component_name(self.planner),
            "lexical_resolver": self._component_name(self.lexical_resolver),
            "realizer": self._component_name(self.realizer),
            "lang_code": self._normalize_lang_code(lang_code),
        }

        construction_id = self._get_value(runtime_payload, "construction_id")
        if self._is_non_empty_string(construction_id):
            debug_info["construction_id"] = str(construction_id)

        slot_map = self._get_value(runtime_payload, "slot_map")
        if isinstance(slot_map, dict):
            debug_info["slot_keys"] = sorted(str(k) for k in slot_map.keys())

        sentence = self._coerce_to_sentence(
            value=realized,
            lang_code=lang_code,
            default_debug_info=debug_info,
        )

        return self._enforce_planner_runtime_metadata(sentence)

    async def _generate_via_legacy_engine(
        self,
        *,
        lang_code: str,
        frame: Frame,
        fallback_reason: str,
    ) -> Sentence:
        """
        Run the legacy direct frame-to-engine path as an explicit fallback only.
        """
        if self.engine is None:
            raise DomainError("Legacy grammar engine fallback is not configured.")

        result = await self.engine.generate(lang_code, frame)

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
        }

        return self._coerce_to_sentence(
            value=result,
            lang_code=lang_code,
            default_debug_info=debug_info,
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

        if isinstance(value, (str, bytes, bytearray, dict, Sentence)):
            return value

        if isinstance(value, (list, tuple)):
            if not value:
                raise DomainError(f"{stage.capitalize()} returned an empty sequence.")
            return value[0]

        return value

    def _coerce_to_sentence(
        self,
        *,
        value: Any,
        lang_code: str,
        default_debug_info: dict[str, Any],
    ) -> Sentence:
        """
        Convert a planner/realizer/engine result into the compatibility Sentence type.
        """
        if isinstance(value, Sentence):
            return Sentence(
                text=str(value.text),
                lang_code=self._normalize_lang_code(value.lang_code or lang_code),
                debug_info=self._merge_debug_info(value.debug_info, default_debug_info),
                generation_time_ms=float(getattr(value, "generation_time_ms", 0.0) or 0.0),
            )

        if isinstance(value, str):
            return Sentence(
                text=value,
                lang_code=self._normalize_lang_code(lang_code),
                debug_info=dict(default_debug_info),
                generation_time_ms=0.0,
            )

        if isinstance(value, dict):
            text = value.get("text")
            compat_debug: dict[str, Any] = {}

            if text is None and "surface_text" in value:
                text = value.get("surface_text")
                compat_debug["legacy_result_key"] = "surface_text"

            if text is None:
                raise DomainError(
                    "Generation result dict is missing required field 'text'."
                )

            extra_debug: dict[str, Any] = dict(default_debug_info)
            for key in (
                "construction_id",
                "renderer_backend",
                "fallback_used",
                "tokens",
                "selected_backend",
                "warnings",
                "confidence",
            ):
                item = value.get(key)
                if item is not None:
                    extra_debug.setdefault(key, item)

            if compat_debug:
                extra_debug.update(compat_debug)

            return Sentence(
                text=str(text),
                lang_code=self._normalize_lang_code(
                    str(value.get("lang_code") or value.get("language") or lang_code)
                ),
                debug_info=self._merge_debug_info(value.get("debug_info"), extra_debug),
                generation_time_ms=float(value.get("generation_time_ms") or 0.0),
            )

        text = getattr(value, "text", None)
        if text is None:
            raise DomainError(
                f"Cannot map result of type '{type(value).__name__}' into Sentence: "
                "missing 'text'."
            )

        debug_info = getattr(value, "debug_info", None)
        result_lang = getattr(value, "lang_code", None) or getattr(value, "language", None)

        extra_debug: dict[str, Any] = dict(default_debug_info)
        for key in (
            "construction_id",
            "renderer_backend",
            "fallback_used",
            "tokens",
            "selected_backend",
            "warnings",
            "confidence",
        ):
            attr = getattr(value, key, None)
            if attr is not None:
                extra_debug.setdefault(key, attr)

        return Sentence(
            text=str(text),
            lang_code=self._normalize_lang_code(str(result_lang or lang_code)),
            debug_info=self._merge_debug_info(debug_info, extra_debug),
            generation_time_ms=float(getattr(value, "generation_time_ms", 0.0) or 0.0),
        )

    def _enforce_planner_runtime_metadata(self, sentence: Sentence) -> Sentence:
        """
        Planner-first results must provide enough metadata to support the
        public response contract and observability.
        """
        debug_info = dict(sentence.debug_info or {})
        missing: list[str] = []

        for key in ("construction_id", "renderer_backend"):
            if not self._is_non_empty_string(debug_info.get(key)):
                missing.append(key)

        if missing:
            raise DomainError(
                "Planner-first generation returned an incomplete runtime result: "
                f"missing {', '.join(missing)}."
            )

        if "selected_backend" not in debug_info and debug_info.get("renderer_backend"):
            debug_info["selected_backend"] = debug_info["renderer_backend"]

        return Sentence(
            text=sentence.text,
            lang_code=self._normalize_lang_code(sentence.lang_code),
            debug_info=debug_info,
            generation_time_ms=float(sentence.generation_time_ms or 0.0),
        )

    def _finalize_sentence(
        self,
        *,
        sentence: Sentence,
        lang_code: str,
        elapsed_ms: float,
        runtime_path: str,
    ) -> Sentence:
        """
        Final cleanup to guarantee a stable Sentence shape.
        """
        text = str(sentence.text or "").strip()
        normalized_lang_code = self._normalize_lang_code(sentence.lang_code or lang_code)

        debug_info = dict(sentence.debug_info or {})
        debug_info["runtime_path"] = runtime_path
        debug_info["lang_code"] = normalized_lang_code

        if runtime_path == PLANNER_FIRST_RUNTIME_PATH:
            debug_info["fallback_used"] = False
        else:
            debug_info["fallback_used"] = True
            debug_info.setdefault("renderer_backend", LEGACY_RENDERER_BACKEND)
            debug_info.setdefault("selected_backend", LEGACY_RENDERER_BACKEND)
            attempted_backends = debug_info.get("attempted_backends")
            if not isinstance(attempted_backends, list) or not attempted_backends:
                debug_info["attempted_backends"] = [LEGACY_RENDERER_BACKEND]

        generation_time_ms = float(sentence.generation_time_ms or 0.0)
        if generation_time_ms <= 0.0:
            generation_time_ms = elapsed_ms
        debug_info["generation_time_ms"] = generation_time_ms

        tokens = debug_info.get("tokens")
        if not isinstance(tokens, list) or any(not isinstance(t, str) for t in tokens):
            debug_info["tokens"] = [part for part in text.split() if part]

        return Sentence(
            text=text,
            lang_code=normalized_lang_code,
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

        return merged

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

    def _component_name(self, component: Any) -> str | None:
        if component is None:
            return None
        return component.__class__.__name__

