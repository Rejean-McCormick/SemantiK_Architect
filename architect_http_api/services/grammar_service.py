# architect_http_api/services/grammar_service.py
import os
import json
import logging
import redis
from typing import Optional

logger = logging.getLogger(__name__)

class GrammarService:
    """
    Service to trigger offline grammar refinement tasks via Redis (CQRS Pattern).
    The actual processing happens in the background worker to ensure API responsiveness.
    """
    
    def __init__(self):
        # Senior Pattern: Externalize Configuration
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.queue_name = "build_queue"
        
        # Initialize Redis connection
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            # Quick ping to verify connection on startup
            self.redis_client.ping()
            logger.info(f"✅ GrammarService connected to Redis at {self.redis_url}")
        except redis.exceptions.ConnectionError:
            logger.critical(f"❌ Redis connection failed at {self.redis_url}. Background tasks will fail.")
            self.redis_client = None

    async def refine_language_async(self, lang_code: str, language_name: str, instructions: str = ""):
        """
        Enqueues a 'refine' job to the Redis queue.
        """
        if not self.redis_client:
            logger.error("⚠️ Redis unavailable. Cannot queue refinement task.")
            return

        # Construct Job Payload
        # Matching the schema expected by builder/worker.py
        job = {
            "type": "refine",
            "lang": lang_code,
            "name": language_name,
            "instructions": instructions
        }

        try:
            # Senior Pattern: Fire and Forget (Producer)
            # rpush adds the job to the tail of the queue
            self.redis_client.rpush(self.queue_name, json.dumps(job))
            
            logger.info(f"🚀 [Queued] AI Refinement for {language_name} ({lang_code}) -> {self.queue_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to enqueue refinement task for {lang_code}: {e}")

# Singleton Instance
grammar_service = GrammarService()