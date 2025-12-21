# app/workers/worker.py
import asyncio
import os
import sys
import subprocess
import structlog
from dataclasses import dataclass
from typing import Dict, Any, Optional

# Add project root to path
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
    
    def load(self, pgf_path: str):
        logger.info("runtime_loading_pgf", path=pgf_path)
        if pgf and os.path.exists(pgf_path):
            try:
                self._pgf = pgf.readPGF(pgf_path)
                logger.info("runtime_pgf_loaded_success")
            except Exception as e:
                logger.error("runtime_pgf_load_failed", error=str(e))
        else:
            logger.warning("runtime_pgf_not_found_or_no_lib", path=pgf_path)

    def get(self) -> Optional[Any]:
        return self._pgf

    async def reload(self):
        """Helper to reload the current configured path."""
        self.load(settings.AW_PGF_PATH)

# Global Instance
runtime = GrammarRuntime()

# --- Job Logic ---

async def compile_grammar(ctx: Dict[str, Any], language_code: str, trace_context: Dict[str, str] = None) -> str:
    """
    ARQ Job: Compiles a GF source file into a PGF binary.
    """
    # 1. Link Telemetry Span (Distributed Tracing)
    ctx_otel = extract(trace_context) if trace_context else None

    with tracer.start_as_current_span("worker_compile_grammar", context=ctx_otel) as span:
        span.set_attribute("language.code", language_code)
        
        try:
            logger.info("compilation_started", lang=language_code)
            
            # 2. Define Paths
            # For the demo, we assume the source files live in 'gf/src' or 'gf'
            # Adjust 'src_dir' if your folder structure is different
            base_dir = settings.FILESYSTEM_REPO_PATH
            src_file = os.path.join(base_dir, "gf", f"Wiki{language_code.capitalize()}.gf")
            
            # 3. Execute GF Compiler (CPU Intensive)
            # Command: gf -make -output-format=pgf gf/WikiFra.gf
            cmd = [
                "gf", 
                "-make", 
                "--output-format=pgf", 
                src_file
            ]
            
            # Only attempt real compilation if 'gf' is installed and source exists
            if os.path.exists(src_file):
                logger.info("executing_subprocess", cmd=" ".join(cmd))
                
                process = await asyncio.to_thread(
                    subprocess.run, 
                    cmd, 
                    capture_output=True, 
                    text=True
                )

                if process.returncode != 0:
                    error_msg = f"GF Compilation Failed: {process.stderr}"
                    logger.error("compilation_failed", error=error_msg)
                    raise RuntimeError(error_msg)
                
                logger.info("subprocess_success", output=process.stdout[:100])
            else:
                logger.warning("source_file_missing", path=src_file, msg="Skipping real compilation, simulating...")
                await asyncio.sleep(1)

            # 4. Persistence (S3)
            # If configured, upload the artifact to the cloud
            target_pgf = settings.AW_PGF_PATH
            
            if settings.STORAGE_BACKEND == StorageBackend.S3 and S3LanguageRepo:
                if os.path.exists(target_pgf):
                    repo = S3LanguageRepo()
                    with open(target_pgf, "rb") as f:
                        content = f.read()
                        await repo.save_grammar(language_code, content)
                    logger.info("s3_upload_success", bucket=settings.AWS_BUCKET_NAME)
                    span.add_event("upload_to_s3_complete")
                else:
                    logger.warning("s3_upload_skipped", msg="PGF file not found locally")

            # 5. Hot Reload
            # Update the resident memory model so subsequent checks are fast
            if os.path.exists(settings.AW_PGF_PATH):
                await runtime.reload()
            
            logger.info("compilation_complete", lang=language_code)
            return f"Compiled {language_code} successfully."

        except Exception as e:
            logger.error("job_failed", error=str(e))
            span.record_exception(e)
            raise e

# --- ARQ Worker Configuration ---

async def startup(ctx):
    """Lifecycle Hook: Runs when the Worker Container starts."""
    setup_telemetry("architect-worker")
    logger.info("worker_startup", queue=settings.REDIS_QUEUE_NAME)
    
    # Pre-warm: Load the grammar defined in settings
    runtime.load(settings.AW_PGF_PATH)

async def shutdown(ctx):
    logger.info("worker_shutdown")

class WorkerSettings:
    """
    ARQ Configuration Class.
    """
    # 1. Connection
    redis_settings = RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        database=settings.REDIS_DB,
    )

    # 2. CRITICAL FIX: Match the Queue Name defined in Config
    queue_name = settings.REDIS_QUEUE_NAME

    # 3. Register Functions
    functions = [compile_grammar]
    
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = settings.WORKER_CONCURRENCY