# app/workers/worker.py
import asyncio
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Callable, Coroutine

import structlog
from arq.connections import RedisSettings

# Add project root to path for reliable imports (container / local)
sys.path.append(os.getcwd())

# Optional: OS-native file watching
try:
    from watchfiles import awatch  # type: ignore
except Exception:
    awatch = None

# Optional: PGF runtime (C-runtime python bindings)
try:
    import pgf  # type: ignore
except Exception:
    pgf = None

from app.shared.config import settings
from app.shared.telemetry import setup_telemetry, get_tracer
from app.shared.lexicon import lexicon

from app.adapters.messaging.redis_broker import RedisMessageBroker
from app.core.domain.events import (
    SystemEvent,
    EventType,
    BuildRequestedPayload,
    BuildFailedPayload,
)

logger = structlog.get_logger()
tracer = get_tracer(__name__)


# -----------------------------
# Path helpers
# -----------------------------
def _normalize_pgf_path(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return value
    if value.endswith(("/", "\\")) or not value.lower().endswith(".pgf"):
        return os.path.join(value, "semantik_architect.pgf")
    return value


def _effective_pgf_path() -> str:
    """
    Prefer explicit env overrides (containers/tests), then validated settings.
    Supports both PGF_PATH (preferred) and legacy AW_PGF_PATH.
    """
    env_path = os.getenv("PGF_PATH") or os.getenv("AW_PGF_PATH")
    if env_path:
        return _normalize_pgf_path(env_path)
    return _normalize_pgf_path(getattr(settings, "PGF_PATH", "") or "")


def _discover_iso_map_path(repo_root: Path) -> Optional[Path]:
    candidates = [
        repo_root / "data" / "config" / "iso_to_wiki.json",
        repo_root / "config" / "iso_to_wiki.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _load_iso_to_wiki(repo_root: Path) -> Dict[str, str]:
    """
    Loads ISO->Wiki GF language mapping if available.
    Normalizes to: { "en": "Eng", "fr": "Fre", ... }
    """
    p = _discover_iso_map_path(repo_root)
    if not p:
        return {}
    try:
        raw = json.loads(p.read_text(encoding="utf-8")) or {}
    except Exception as e:
        logger.warning("iso_to_wiki_load_failed", path=str(p), error=str(e))
        return {}

    out: Dict[str, str] = {}
    for k, v in (raw or {}).items():
        if not isinstance(k, str):
            continue
        key = k.lower().strip()
        if not key:
            continue

        if isinstance(v, dict):
            wiki = v.get("wiki")
            if isinstance(wiki, str) and wiki.strip():
                out[key] = wiki.strip().replace("Wiki", "")
        elif isinstance(v, str) and v.strip():
            out[key] = v.strip().replace("Wiki", "")
    return out


def _resolve_wiki_code(lang_code: str, repo_root: Path) -> str:
    code = (lang_code or "").lower().strip()
    iso_map = _load_iso_to_wiki(repo_root)
    mapped = iso_map.get(code)
    if mapped:
        return mapped
    # Fallback: ISO 'eng' -> 'Eng', 'xyz' -> 'Xyz'
    return (lang_code or "").title()


def _resolve_src_file(lang_code: str, repo_root: Path) -> Path:
    wiki_code = _resolve_wiki_code(lang_code, repo_root)
    # Prefer canonical generated output; fall back to legacy gf/ location.
    candidates = [
        repo_root / "generated" / "src" / f"Wiki{wiki_code}.gf",
        repo_root / "gf" / f"Wiki{wiki_code}.gf",
    ]
    for p in candidates:
        if p.exists():
            return p
    # return first candidate as "expected" location for error messages
    return candidates[0]


def _map_build_strategy(strategy: str) -> tuple[str, bool]:
    """
    Returns (orchestrator_strategy, clean_flag).

    Worker accepts legacy values ("fast/full/incremental") and maps them to
    orchestrator strategies ("AUTO/HIGH_ROAD/SAFE_MODE").
    """
    s = (strategy or "").strip().lower()

    if s in {"", "auto", "fast", "inc", "incremental"}:
        return "AUTO", False
    if s in {"full", "clean"}:
        return "AUTO", True

    if s in {"high", "highroad", "high-road", "high_road"}:
        return "HIGH_ROAD", False
    if s in {"safe", "safemode", "safe-mode", "safe_mode"}:
        return "SAFE_MODE", False

    # Pass-through for implementation-defined values (prefer uppercase)
    return (strategy or "AUTO").strip().upper(), False


# -----------------------------
# Runtime: in-memory PGF cache
# -----------------------------
@dataclass
class GrammarRuntime:
    """
    Holds a loaded PGF in memory (if pgf runtime is installed).
    Also supports "zombie language" detection based on the Everything Matrix verdict.
    """

    _pgf: Optional[Any] = None
    _last_mtime: float = 0.0

    def load(self, pgf_path: str) -> None:
        pgf_path = _normalize_pgf_path(pgf_path)
        logger.info("runtime_loading_pgf", path=pgf_path)

        if not pgf:
            logger.warning("runtime_pgf_lib_missing", note="python 'pgf' module not installed")
            return

        if not os.path.exists(pgf_path):
            logger.warning("runtime_pgf_missing", path=pgf_path)
            return

        try:
            self._last_mtime = os.path.getmtime(pgf_path)
            raw_pgf = pgf.readPGF(pgf_path)

            # Detect (but do not delete) zombie languages using Everything Matrix
            matrix_path = Path(settings.FILESYSTEM_REPO_PATH) / "data" / "indices" / "everything_matrix.json"
            if matrix_path.exists():
                try:
                    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
                    languages = matrix.get("languages", {}) or {}
                    for lang_name in list(getattr(raw_pgf, "languages", {}).keys()):
                        iso_guess = (lang_name[-3:] if isinstance(lang_name, str) else "").lower()
                        verdict = (languages.get(iso_guess, {}) or {}).get("verdict", {}) or {}
                        runnable = verdict.get("runnable", True)
                        if not runnable:
                            logger.warning(
                                "runtime_zombie_language_detected",
                                lang=lang_name,
                                iso=iso_guess,
                                reason="matrix.verdict.runnable=False",
                            )
                except Exception as e:
                    logger.error("runtime_matrix_filter_failed", error=str(e))
            else:
                logger.warning("runtime_matrix_missing", path=str(matrix_path))

            self._pgf = raw_pgf
            logger.info("runtime_pgf_loaded_success", active_languages=list(self._pgf.languages.keys()))
        except Exception as e:
            logger.error("runtime_pgf_load_failed", error=str(e))

    def get(self) -> Optional[Any]:
        return self._pgf

    async def reload(self) -> None:
        pgf_path = _effective_pgf_path()
        logger.info("runtime_reloading_triggered", path=pgf_path)
        self.load(pgf_path)


runtime = GrammarRuntime()


# -----------------------------
# Subprocess helpers
# -----------------------------
async def _run_cmd(
    argv: list[str],
    *,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    timeout_sec: Optional[int] = None,
) -> Any:
    """
    Run a blocking subprocess in a thread.
    Captures stdout/stderr for logging and error reporting.
    """

    def _runner() -> subprocess.CompletedProcess:
        return subprocess.run(
            argv,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )

    logger.info("subprocess_exec", argv=" ".join(argv), cwd=cwd)
    return await asyncio.to_thread(_runner)


async def _run_indexer(repo_root: Path, *, langs: list[str]) -> None:
    indexer = repo_root / "tools" / "everything_matrix" / "build_index.py"
    if not indexer.exists():
        raise RuntimeError(f"Indexer missing: {indexer}")

    argv = [sys.executable, "-u", str(indexer)]
    if langs:
        argv += ["--langs", *langs]

    proc = await _run_cmd(argv, cwd=str(repo_root))
    if getattr(proc, "returncode", 1) != 0:
        err = (getattr(proc, "stderr", "") or "").strip()
        out = (getattr(proc, "stdout", "") or "").strip()
        raise RuntimeError(f"Indexing failed:\n{err or out}")


async def _run_orchestrator(repo_root: Path, *, langs: list[str], strategy: str, clean: bool) -> None:
    """
    In-process orchestrator call (no script-path dependency).
    """
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    def _runner() -> Path:
        from builder.orchestrator import build_pgf  # local import to honor sys.path injection

        return build_pgf(
            strategy=(strategy or "AUTO").strip().upper(),
            langs=langs or None,
            clean=bool(clean),
            verbose=False,
            max_workers=None,
            no_preflight=False,
            regen_safe=False,
        )

    try:
        pgf_path = await asyncio.to_thread(_runner)
        logger.info("orchestrator_completed", pgf_path=str(pgf_path), langs=langs, strategy=strategy, clean=clean)
    except SystemExit as e:
        raise RuntimeError(f"Build orchestrator failed (SystemExit code={getattr(e, 'code', None)})") from e
    except Exception as e:
        raise RuntimeError(f"Build orchestrator failed: {e}") from e


# -----------------------------
# ARQ Jobs
# -----------------------------
async def build_language(ctx: Dict[str, Any], request: Dict[str, Any]) -> str:
    """
    Canonical job triggered by the Event Bus bridge.

    Pipeline:
      1) Index knowledge layer: tools/everything_matrix/build_index.py
      2) Compile/link grammar layer (in-process): builder.orchestrator.build_pgf
      3) Reload in-memory runtime if available
      4) Emit BUILD_COMPLETED / BUILD_FAILED
    """
    broker: Optional[RedisMessageBroker] = ctx.get("event_broker")

    payload = BuildRequestedPayload(**request)
    lang_code = payload.lang_code
    requested_strategy = (payload.strategy or "auto").strip()

    orch_strategy, clean = _map_build_strategy(requested_strategy)

    with tracer.start_as_current_span("worker_build_language") as span:
        span.set_attribute("language.code", lang_code)
        span.set_attribute("build.strategy.requested", requested_strategy)
        span.set_attribute("build.strategy.orchestrator", orch_strategy)
        span.set_attribute("build.clean", bool(clean))

        try:
            logger.info(
                "build_job_started",
                lang=lang_code,
                strategy=requested_strategy,
                orch_strategy=orch_strategy,
                clean=clean,
            )

            if broker:
                await broker.publish(
                    SystemEvent(
                        type=EventType.BUILD_STARTED,
                        payload={
                            "lang_code": lang_code,
                            "strategy": requested_strategy,
                            "requester_id": payload.requester_id,
                        },
                    )
                )

            repo_root = Path(settings.FILESYSTEM_REPO_PATH)

            # Step 1: Index (scoped)
            await _run_indexer(repo_root, langs=[lang_code])

            # Step 2: Build Orchestrator (scoped, in-process)
            await _run_orchestrator(repo_root, langs=[lang_code], strategy=orch_strategy, clean=clean)

            # Validate artifact
            pgf_path = _effective_pgf_path()
            if not os.path.exists(pgf_path):
                raise RuntimeError(f"Build completed but PGF artifact missing at: {pgf_path}")

            # Hot reload (best-effort)
            await runtime.reload()

            logger.info("build_job_completed", lang=lang_code, pgf_path=pgf_path)

            if broker:
                await broker.publish(
                    SystemEvent(
                        type=EventType.BUILD_COMPLETED,
                        payload={"lang_code": lang_code, "strategy": requested_strategy, "pgf_path": pgf_path},
                    )
                )

            return f"Built {lang_code} successfully."

        except Exception as e:
            logger.error("build_job_failed", lang=lang_code, error=str(e))
            span.record_exception(e)

            if broker:
                fail = BuildFailedPayload(
                    lang_code=lang_code,
                    error_code="WORKER_BUILD_FAILED",
                    details=str(e),
                )
                await broker.publish(
                    SystemEvent(
                        type=EventType.BUILD_FAILED,
                        payload=fail.model_dump(),
                    )
                )
            raise


# Back-compat job: compile a single language (kept for older callers)
async def compile_grammar(ctx: Dict[str, Any], language_code: str) -> str:
    repo_root = Path(settings.FILESYSTEM_REPO_PATH)

    # Scoped incremental build (no events)
    await _run_indexer(repo_root, langs=[language_code])
    await _run_orchestrator(repo_root, langs=[language_code], strategy="AUTO", clean=False)

    pgf_path = _effective_pgf_path()
    if not os.path.exists(pgf_path):
        raise RuntimeError(f"Build completed but PGF artifact missing at: {pgf_path}")

    await runtime.reload()
    return f"Compiled {language_code} successfully."


# -----------------------------
# Background tasks
# -----------------------------
async def watch_grammar_file(_: Dict[str, Any]) -> None:
    """
    Watches settings.PGF_PATH and reloads runtime when it changes.
    Uses watchfiles when available, otherwise polling.
    """
    pgf_path = _effective_pgf_path()
    pgf_dir = os.path.dirname(pgf_path)

    if not os.path.exists(pgf_dir):
        logger.warning("watcher_dir_missing", path=pgf_dir)
        return

    logger.info("watcher_started", path=pgf_path, mechanism="watchfiles" if awatch else "polling")

    if awatch:
        try:
            async for changes in awatch(pgf_dir):
                for change_type, file_path in changes:
                    if os.path.abspath(file_path) == os.path.abspath(pgf_path):
                        logger.info("watcher_detected_change", file=file_path, type=change_type)
                        await asyncio.sleep(0.1)
                        runtime.load(pgf_path)
        except asyncio.CancelledError:
            logger.info("watcher_stopped")
        except Exception as e:
            logger.error("watcher_crashed", error=str(e))
    else:
        try:
            while True:
                current_mtime = os.path.getmtime(pgf_path) if os.path.exists(pgf_path) else 0.0
                if current_mtime > runtime._last_mtime:
                    logger.info("watcher_polling_change", old=runtime._last_mtime, new=current_mtime)
                    runtime.load(pgf_path)
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            logger.info("watcher_stopped")
        except Exception as e:
            logger.error("watcher_error", error=str(e))


# -----------------------------
# Event Bus -> ARQ bridge
# -----------------------------
async def _event_dedupe(ctx: Dict[str, Any], event_id: str, *, ttl_sec: int = 3600) -> bool:
    """
    True if event is new; False if already seen.
    Uses Redis SET NX with TTL for idempotency.
    """
    redis = ctx.get("redis")
    if not redis or not event_id:
        return True

    key = f"event_seen:{event_id}"
    try:
        ok = await redis.set(key, "1", ex=ttl_sec, nx=True)  # type: ignore[attr-defined]
        return bool(ok)
    except Exception as e:
        logger.warning("event_dedupe_failed", event_id=event_id, error=str(e))
        return True


async def _bridge_handler_factory(ctx: Dict[str, Any]) -> Callable[[SystemEvent], Coroutine[Any, Any, None]]:
    async def handler(event: SystemEvent) -> None:
        if not await _event_dedupe(ctx, event.id):
            logger.info("bridge_drop_duplicate_event", event_id=event.id, type=event.type)
            return

        try:
            payload = BuildRequestedPayload(**(event.payload or {}))
        except Exception as e:
            logger.error("bridge_bad_payload", event_id=event.id, error=str(e), payload=event.payload)
            return

        request = {
            "lang_code": payload.lang_code,
            "strategy": payload.strategy,
            "requester_id": payload.requester_id,
            "event_id": event.id,
            "trace_id": event.trace_id,
        }

        redis = ctx.get("redis")
        if not redis:
            logger.error("bridge_no_arq_redis", note="ctx['redis'] missing; cannot enqueue")
            return

        job_id = await redis.enqueue_job("build_language", request)  # type: ignore[attr-defined]
        logger.info(
            "bridge_enqueued_job",
            event_id=event.id,
            job_id=job_id,
            lang=payload.lang_code,
            strategy=payload.strategy,
        )

    return handler


async def _run_bridge(ctx: Dict[str, Any]) -> None:
    broker: RedisMessageBroker = ctx["event_broker"]
    handler = await _bridge_handler_factory(ctx)

    logger.info("bridge_subscribing", event_type=EventType.BUILD_REQUESTED)
    await broker.subscribe(EventType.BUILD_REQUESTED, handler)


# -----------------------------
# ARQ lifecycle
# -----------------------------
async def startup(ctx: Dict[str, Any]) -> None:
    setup_telemetry("architect-worker")
    logger.info("worker_startup", queue=settings.REDIS_QUEUE_NAME)

    broker = RedisMessageBroker()
    await broker.connect()
    ctx["event_broker"] = broker

    runtime.load(_effective_pgf_path())

    try:
        lexicon.load_language("eng")
    except Exception as e:
        logger.warning("lexicon_warm_failed", error=str(e))

    ctx["bridge_task"] = asyncio.create_task(_run_bridge(ctx))
    ctx["watcher_task"] = asyncio.create_task(watch_grammar_file(ctx))


async def shutdown(ctx: Dict[str, Any]) -> None:
    logger.info("worker_shutdown")

    for task_name in ("bridge_task", "watcher_task"):
        task = ctx.get(task_name)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error("shutdown_task_error", task=task_name, error=str(e))

    broker: Optional[RedisMessageBroker] = ctx.get("event_broker")
    if broker:
        try:
            await broker.disconnect()
        except Exception as e:
            logger.error("broker_disconnect_failed", error=str(e))


class WorkerSettings:
    """
    ARQ configuration.
    """

    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    queue_name = settings.REDIS_QUEUE_NAME

    # Job registry
    functions = [build_language, compile_grammar]

    on_startup = startup
    on_shutdown = shutdown

    max_jobs = settings.WORKER_CONCURRENCY