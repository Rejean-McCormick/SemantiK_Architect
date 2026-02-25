# tools/language_health/models.py
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal, Optional

CompileStatus = Literal["VALID", "BROKEN", "SKIPPED"]
RuntimeStatus = Literal["PASS", "FAIL"]
OverallStatus = Literal["OK", "FAIL", "SKIPPED"]


@dataclass(frozen=True, slots=True)
class CompileResult:
    """
    Result of compiling a single GF language module (e.g. generated/src/WikiEng.gf).
    """
    gf_lang: str
    filename: str  # repo-relative path (e.g. generated/src/WikiEng.gf)
    status: CompileStatus
    error: Optional[str] = None
    duration_s: float = 0.0
    file_hash: str = ""
    iso2: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def is_ok(self) -> bool:
        return self.status in ("VALID", "SKIPPED")

    @property
    def is_skipped(self) -> bool:
        return self.status == "SKIPPED"

    @property
    def is_broken(self) -> bool:
        return self.status == "BROKEN"


@dataclass(frozen=True, slots=True)
class RuntimeResult:
    """
    Result of POSTing a small test frame to /generate/{lang}.
    """
    api_lang: str
    status: RuntimeStatus
    http_status: Optional[int] = None
    duration_ms: float = 0.0
    error: Optional[str] = None
    sample_text: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def is_ok(self) -> bool:
        return self.status == "PASS"

    @property
    def is_fail(self) -> bool:
        return self.status == "FAIL"


@dataclass(frozen=True, slots=True)
class HealthRow:
    """
    Combined view of compile + runtime health for a language.

    Semantics:
      - FAIL if compile BROKEN or runtime FAIL
      - OK if any check ran and did not fail (compile VALID, or runtime PASS)
      - SKIPPED if nothing ran, or only compile was SKIPPED with no runtime result
    """
    gf_lang: Optional[str] = None
    api_lang: Optional[str] = None
    compile: Optional[CompileResult] = None
    runtime: Optional[RuntimeResult] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "gf_lang": self.gf_lang,
            "api_lang": self.api_lang,
            "overall": self.overall_status(),
            "compile": self.compile.to_dict() if self.compile else None,
            "runtime": self.runtime.to_dict() if self.runtime else None,
        }

    @property
    def lang(self) -> Optional[str]:
        """Preferred language identifier for display (API code first, else GF wiki code)."""
        return self.api_lang or self.gf_lang

    def overall_status(self) -> OverallStatus:
        if self.compile and self.compile.status == "BROKEN":
            return "FAIL"
        if self.runtime and self.runtime.status == "FAIL":
            return "FAIL"

        # Any successful runtime implies OK.
        if self.runtime and self.runtime.status == "PASS":
            return "OK"

        # Otherwise rely on compile result if present.
        if self.compile:
            if self.compile.status == "VALID":
                return "OK"
            if self.compile.status == "SKIPPED":
                return "SKIPPED"

        # Nothing ran.
        return "SKIPPED"

    def failure_reason(self) -> Optional[str]:
        """Return the most relevant failure reason, if any."""
        if self.compile and self.compile.status == "BROKEN":
            return self.compile.error
        if self.runtime and self.runtime.status == "FAIL":
            return self.runtime.error
        return None


__all__ = [
    "CompileStatus",
    "RuntimeStatus",
    "OverallStatus",
    "CompileResult",
    "RuntimeResult",
    "HealthRow",
]