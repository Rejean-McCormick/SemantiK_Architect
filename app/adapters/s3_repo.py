# app/adapters/s3_repo.py
import asyncio
import json
import boto3
from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# [FIX] Import from the consolidated ports package
from app.core.ports import LanguageRepo, LexiconRepo
from app.core.domain.models import LexiconEntry
from app.shared.config import settings
from app.shared.telemetry import get_tracer

tracer = get_tracer(__name__)

class S3LanguageRepo(LanguageRepo, LexiconRepo):
    """
    Production Persistence Adapter backed by AWS S3.
    - Acts as LanguageRepo (Metadata & Grammars)
    - Acts as LexiconRepo (Vocabulary - currently stubs/limited)
    """

    def __init__(self):
        # Initialize Boto3 Client
        self.s3_client = boto3.client(
            "s3",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self.bucket = settings.AWS_BUCKET_NAME

    # =========================================================
    # PART 1: LanguageRepo Implementation (Zone A)
    # =========================================================

    async def list_languages(self) -> List[Dict[str, Any]]:
        """
        Fetches 'data/indices/everything_matrix.json' from S3.
        """
        key = "data/indices/everything_matrix.json"
        try:
            content_bytes = await asyncio.to_thread(self._download_sync, key)
            data = json.loads(content_bytes.decode('utf-8'))
            
            languages = []
            for iso_code, details in data.get("languages", {}).items():
                meta = details.get("meta", {})
                languages.append({
                    "code": meta.get("iso", iso_code),
                    "name": meta.get("name", iso_code.upper()),
                    "z_id": meta.get("z_id", None)
                })
            return sorted(languages, key=lambda x: x["name"])
        except (ClientError, FileNotFoundError):
            # Fallback if matrix missing
            return []

    async def save_grammar(self, language_code: str, content: str) -> None:
        """Saves the GF source file (.gf) to S3."""
        key = f"sources/{language_code}/Wiki{language_code}.gf"
        await asyncio.to_thread(self._upload_sync, key, content.encode('utf-8'))

    async def get_grammar(self, language_code: str) -> Optional[str]:
        """Retrieves the GF source file."""
        key = f"sources/{language_code}/Wiki{language_code}.gf"
        try:
            data = await asyncio.to_thread(self._download_sync, key)
            return data.decode('utf-8')
        except (ClientError, FileNotFoundError):
            return None

    # =========================================================
    # PART 2: LexiconRepo Implementation (Zone B)
    # =========================================================
    # Note: Using S3 for granular word lookups is slow. 
    # In production, this should likely connect to DynamoDB or cache heavily.
    
    async def get_entry(self, iso_code: str, word: str) -> Optional[LexiconEntry]:
        """Stub: S3 is not optimized for single word lookups."""
        return None

    async def save_entry(self, iso_code: str, entry: LexiconEntry) -> None:
        """Stub: Would require reading/writing huge JSON blobs."""
        pass

    async def get_entries_by_concept(self, lang_code: str, qid: str) -> List[LexiconEntry]:
        """Stub."""
        return []

    # =========================================================
    # PART 3: Infrastructure / Helpers
    # =========================================================

    async def health_check(self) -> bool:
        """Checks connection by listing 1 object."""
        try:
            await asyncio.to_thread(self.s3_client.list_objects_v2, Bucket=self.bucket, MaxKeys=1)
            return True
        except Exception:
            return False

    async def save_pgf(self, language_code: str, binary_content: bytes) -> None:
        """Legacy/Extra: Uploads compiled PGF binary."""
        key = f"grammars/{language_code}.pgf"
        await asyncio.to_thread(self._upload_sync, key, binary_content)

    # --- Synchronous Helpers (executed in thread pool) ---

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(ClientError)
    )
    def _upload_sync(self, key: str, data: bytes):
        """Sync boto3 upload with retries."""
        self.s3_client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            # ContentType="application/octet-stream"
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(ClientError)
    )
    def _download_sync(self, key: str) -> bytes:
        """Sync boto3 download with retries."""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except ClientError as e:
            if e.response['Error']['Code'] in ("404", "NoSuchKey"):
                raise FileNotFoundError(f"Key {key} not found.")
            raise e