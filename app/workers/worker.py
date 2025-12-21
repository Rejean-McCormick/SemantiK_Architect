import asyncio
import os
import sys
import subprocess
import structlog
import time
from dataclasses import dataclass
from typing import Dict, Any, Optional

# Add project root to path for reliable imports
sys.path.append(os.getcwd())

from arq.connections import RedisSettings
from opentelemetry.propagate import extract
try:
    import pgf
except ImportError:
    pgf = None

from app.shared.config import settings, StorageBackend
from app.shared.telemetry import setup_telemetry, get_tracer

# Conditional Import for S3 to avoid crashes if adapter is missing
try:
    from app.adapters.s3_repo import S3LanguageRepo
except ImportError:
    S3LanguageRepo = None

logger = structlog.get_logger()
tracer = get_tracer(__name__)

# --- Lazy Singleton Runtime ---
@dataclass
class GrammarRuntime:
    """
    Singleton that holds loaded PGF binaries in memory.
    Prevents 'Cold Start' latency for validation/generation tasks.
    """
    _pgf: Optional[Any] = None
    _last_mtime: float = 0.0
    
    def load(self, pgf_path: str):
        logger.info("runtime_loading_pgf", path=pgf_path)
        if pgf and os.path.exists(pgf_path):
            try:
                # Update mtime tracking
                self._last_mtime = os.path.getmtime(pgf_path)
                self._pgf = pgf.readPGF(pgf_path)
                logger.info("runtime_pgf_loaded_success", languages=list(self._pgf.languages.keys()))
            except Exception as e:
                logger.error("runtime_pgf_load_failed", error=str(e))
        else:
            logger.warning("runtime_pgf_not_found_or_no_lib", path=pgf_path)

    def get(self) -> Optional[Any]:
        return self._pgf

    async def reload(self):
        """Helper to reload the current configured path."""
        logger.info("runtime_reloading_triggered")
        self.load(settings.AW_PGF_PATH)
    
    def check_for_updates(self, pgf_path: str) -> bool:
        """Checks if the file on disk is newer than the loaded one."""
        if not os.path.exists(pgf_path):
            return False
        
        current_mtime = os.path.getmtime(pgf_path)
        if current_mtime > self._last_mtime:
            logger.info("runtime_detected_file_change", old=self._last_mtime, new=current_mtime)
            return True
        return False

# Global Instance
runtime = GrammarRuntime()

# --- Job Logic ---

async def compile_grammar(ctx: Dict[str, Any], language_code: str, trace_context: Dict[str, str] = None) -> str:
    """
    ARQ Job: Compiles a single GF source file (Tier 2/3 dev mode).
    Note: Production builds are handled by build_orchestrator.py.
    """
    # 1. Link Telemetry Span (Distributed Tracing)
    ctx_otel = extract(trace_context) if trace_context else None

    with tracer.start_as_current_span("worker_compile_grammar", context=ctx_otel) as span:
        span.set_attribute("language.code", language_code)
        
        try:
            logger.info("compilation_started", lang=language_code)
            
            # 2. Define Paths
            base_dir = settings.FILESYSTEM_REPO_PATH
            # Adjusted path to match the orchestrator's structure
            src_file = os.path.join(base_dir, "gf", f"Wiki{language_code.capitalize()}.gf")
            
            # 3. Execute GF Compiler
            # Using -batch to prevent hanging
            cmd = [
                "gf", 
                "-batch",
                "-make", 
                "--output-format=pgf", 
                src_file
            ]
            
            if os.path.exists(src_file):
                logger.info("executing_subprocess", cmd=" ".join(cmd))
                
                process = await asyncio.to_thread(
                    subprocess.run, 
                    cmd, 
                    capture_output=True, 
                    text=True,
                    cwd=os.path.join(base_dir, "gf") # Run inside gf/ dir
                )

                if process.returncode != 0:
                    error_msg = f"GF Compilation Failed: {process.stderr}"
                    logger.error("compilation_failed", error=error_msg)
                    raise RuntimeError(error_msg)
                
                logger.info("subprocess_success", output=process.stdout[:100])
            else:
                logger.warning("source_file_missing", path=src_file)
                return "Source file missing"

            # 4. Persistence (S3)
            if settings.STORAGE_BACKEND == StorageBackend.S3 and S3LanguageRepo:
                target_pgf = settings.AW_PGF_PATH
                if os.path.exists(target_pgf):
                    repo = S3LanguageRepo()
                    with open(target_pgf, "rb") as f:
                        content = f.read()
                        await repo.save_grammar(language_code, content)
                    logger.info("s3_upload_success", bucket=settings.AWS_BUCKET_NAME)
                else:
                    logger.warning("s3_upload_skipped", msg="PGF file not found locally")

            # 5. Hot Reload
            # Explicit reload after compilation job
            if os.path.exists(settings.AW_PGF_PATH):
                await runtime.reload()
            
            logger.info("compilation_complete", lang=language_code)
            return f"Compiled {language_code} successfully."

        except Exception as e:
            logger.error("job_failed", error=str(e))
            span.record_exception(e)
            raise e

# --- Background Tasks ---

async def watch_grammar_file(ctx):
    """
    Background Task: Polls the PGF binary for changes.
    This ensures the worker picks up builds from build_orchestrator.py.
    """
    pgf_path = settings.AW_PGF_PATH
    logger.info("watcher_started", path=pgf_path)
    
    while True:
        try:
            if runtime.check_for_updates(pgf_path):
                logger.info("watcher_triggering_reload")
                runtime.load(pgf_path)
            
            # Poll every 5 seconds (Low overhead)
            await asyncio.sleep(5)
        except asyncio.CancelledError:
            logger.info("watcher_stopped")
            break
        except Exception as e:
            logger.error("watcher_error", error=str(e))
            await asyncio.sleep(10)

# --- ARQ Worker Configuration ---

async def startup(ctx):
    """Lifecycle Hook: Runs when the Worker Container starts."""
    setup_telemetry("architect-worker")
    logger.info("worker_startup", queue=settings.REDIS_QUEUE_NAME)
    
    # 1. Initial Load
    runtime.load(settings.AW_PGF_PATH)

    # 2. Start Background Watcher
    ctx['watcher_task'] = asyncio.create_task(watch_grammar_file(ctx))

async def shutdown(ctx):
    logger.info("worker_shutdown")
    if 'watcher_task' in ctx:
        ctx['watcher_task'].cancel()
        await ctx['watcher_task']

class WorkerSettings:
    """
    ARQ Configuration Class.
    """
    redis_settings = RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        database=settings.REDIS_DB,
    )

    queue_name = settings.REDIS_QUEUE_NAME
    functions = [compile_grammar]
    
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = settings.WORKER_CONCURRENCY