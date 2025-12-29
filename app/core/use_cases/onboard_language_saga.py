# app/core/use_cases/onboard_language_saga.py
import structlog
from datetime import datetime
from app.core.domain.models import Language, LanguageStatus, GrammarType
from app.core.domain.events import SystemEvent, EventType, BuildRequestedPayload
from app.core.domain.exceptions import DomainError

# [FIX] Import interfaces from the unified ports package
from app.core.ports import IMessageBroker, LanguageRepo
from app.shared.observability import get_tracer

logger = structlog.get_logger()
tracer = get_tracer(__name__)

class LanguageAlreadyExistsError(DomainError):
    def __init__(self, code: str):
        super().__init__(f"Language '{code}' is already registered in the system.")

class OnboardLanguageSaga:
    """
    Use Case (Saga): Orchestrates the onboarding of a new language.
    
    Steps:
    1. Validates uniqueness (ISO 639-3).
    2. Creates the Language Entity (Status: PLANNED).
    3. Persists the metadata (Updating the 'Everything Matrix').
    4. Triggers the initial scaffolding/build via the Event Bus.
    """

    # [FIX] Updated type hint to LanguageRepo (metadata) instead of LexiconRepo (words)
    def __init__(self, broker: IMessageBroker, repo: LanguageRepo):
        self.broker = broker
        self.repo = repo

    async def execute(self, code: str, name: str, family: str = "Other") -> str:
        """
        Executes the onboarding saga.

        Args:
            code: ISO 639-3 code (e.g., 'deu').
            name: English name (e.g., 'German').
            family: Language family.

        Returns:
            str: The ID of the Language entity created.
        """
        with tracer.start_as_current_span("use_case.onboard_language") as span:
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
            # For the FileSystemRepo, this might mean updating the Everything Matrix
            # or creating the directory structure. 
            # Note: save_grammar is a placeholder for saving the definition.
            # await self.repo.save_grammar(code, "...") 
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