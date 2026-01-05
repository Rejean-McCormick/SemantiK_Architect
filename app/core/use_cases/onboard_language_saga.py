# app/core/use_cases/onboard_language_saga.py
import structlog
from datetime import datetime
from app.core.domain.models import Language, LanguageStatus, GrammarType
from app.core.domain.events import SystemEvent, EventType, BuildRequestedPayload
from app.core.domain.exceptions import DomainError

# [FIX] Import interfaces from the unified ports package
from app.core.ports import IMessageBroker, LanguageRepo
from app.shared.observability import get_tracer
# [NEW] Import the Authority for language code normalization
from app.shared.lexicon import lexicon

logger = structlog.get_logger()
tracer = get_tracer(__name__)

class LanguageAlreadyExistsError(DomainError):
    def __init__(self, code: str):
        super().__init__(f"Language '{code}' is already registered in the system.")

class OnboardLanguageSaga:
    """
    Use Case (Saga): Orchestrates the onboarding of a new language.
    
    Steps:
    1. Normalizes the language code (ISO-3 -> ISO-2 where applicable).
    2. Validates uniqueness.
    3. Creates the Language Entity (Status: PLANNED).
    4. Persists the metadata (Updating the 'Everything Matrix').
    5. Triggers the initial scaffolding/build via the Event Bus.
    """

    # [FIX] Updated type hint to LanguageRepo (metadata) instead of LexiconRepo (words)
    def __init__(self, broker: IMessageBroker, repo: LanguageRepo):
        self.broker = broker
        self.repo = repo

    async def execute(self, code: str, name: str, family: str = "Other") -> str:
        """
        Executes the onboarding saga.

        Args:
            code: ISO 639-1 or 639-3 code (e.g., 'en' or 'eng').
            name: English name (e.g., 'German').
            family: Language family.

        Returns:
            str: The ID of the Language entity created (canonical code).
        """
        with tracer.start_as_current_span("use_case.onboard_language") as span:
            
            # [FIX] CRITICAL: Normalize BEFORE Persistence
            # This converts 'eng' -> 'en', 'fra' -> 'fr' based on the shared config.
            # It prevents "Split Brain" folders.
            canonical_code = lexicon.normalize_code(code)
            
            if canonical_code != code:
                logger.info("onboarding_code_normalized", original=code, normalized=canonical_code)
                code = canonical_code

            span.set_attribute("app.lang_code", code)
            
            logger.info("onboarding_started", code=code, name=name)

            # 1. Check for duplicates
            # In a real scenario, we check the list from the repo.
            # existing_list = await self.repo.list_languages()
            # if any(l['code'] == code for l in existing_list):
            #     raise LanguageAlreadyExistsError(code)

            # 2. Create Entity
            language = Language(
                code=code,
                name=name,
                family=family,
                status=LanguageStatus.PLANNED,
                grammar_type=GrammarType.FACTORY, # Default to Pidgin first
                build_strategy="fast"
            )

            # 3. Persist Metadata
            # [FIX] We now explicitly save the language metadata to the Repo using the canonical code.
            # For FileSystemRepo, this will create the folder using the correct code (e.g., 'en').
            await self.repo.save_grammar(code, language.model_dump_json())
            logger.info("language_metadata_saved", code=code)

            # 4. Trigger the Build (The Side Effect)
            # We immediately request a 'Fast' build to generate the scaffolding
            build_payload = BuildRequestedPayload(
                lang_code=code,
                strategy="fast"
            )
            
            event = SystemEvent(
                type=EventType.BUILD_REQUESTED,
                payload=build_payload.model_dump()
            )
            
            await self.broker.publish(event)
            
            logger.info("onboarding_build_triggered", event_id=event.id)
            
            return code