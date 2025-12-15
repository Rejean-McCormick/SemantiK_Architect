# builder\worker.py
import os
import sys
import json
import time
import redis
import logging

# Ensure we can import modules from the root directory
sys.path.append(os.getcwd())

from builder import compiler, healer

# --- Configuration ---
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME = "build_queue"

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [WORKER] - %(levelname)s - %(message)s"
)
logger = logging.getLogger("worker")

# --- Redis Connection ---
try:
    r = redis.from_url(REDIS_URL)
    logger.info(f"✅ Connected to Redis at {REDIS_URL}")
except Exception as e:
    logger.critical(f"❌ Failed to connect to Redis: {e}")
    sys.exit(1)

def process_job(job_data):
    """
    Executes the build task based on the job type.
    """
    job_type = job_data.get("type")
    lang = job_data.get("lang")
    
    logger.info(f"🔧 Processing Job: {job_type} (Lang: {lang})")

    start_time = time.time()
    success = False

    if job_type == "compile_all":
        # Full System Build
        logger.info("🔨 Starting Full Compile...")
        success = compiler.run()
        
        if not success:
            logger.warning("⚠️ Compile failed. Triggering Healer...")
            healer.run_healing_round()
            logger.info("🔄 Retrying Compile after healing...")
            success = compiler.run()

    elif job_type == "compile_one":
        # Single Language Build
        if not lang:
            logger.error("❌ Job missing 'lang' parameter.")
            return

        logger.info(f"🔨 Compiling Single Language: {lang}...")
        # Assuming compiler.py has a method for single compilation. 
        # If not, we fall back to the main run() or you can add compiler.compile_one(lang)
        # For now, we reuse the robust logic usually found in strategies.
        success = compiler.run(target_lang=lang) 

    duration = time.time() - start_time
    status_emoji = "✅" if success else "❌"
    logger.info(f"{status_emoji} Job Finished in {duration:.2f}s")

def run():
    """
    Main Loop: Pops jobs from Redis and executes them.
    """
    logger.info(f"👷 Worker started. Listening on '{QUEUE_NAME}'...")
    
    while True:
        try:
            # Blocking pop: Waits until a job is available
            # Returns tuple: (queue_name, data_bytes)
            result = r.blpop(QUEUE_NAME, timeout=5)
            
            if result:
                _, data = result
                job = json.loads(data)
                process_job(job)
            
            # Small sleep not strictly necessary with blpop, but good for safety
            # time.sleep(0.1) 

        except redis.exceptions.ConnectionError:
            logger.error("❌ Redis connection lost. Retrying in 5s...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"❌ Unexpected Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    run()