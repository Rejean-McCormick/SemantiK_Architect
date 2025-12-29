# app/shared/container.py
from dependency_injector import containers, providers
from app.shared.config import settings

# --- Adapters ---
from app.adapters.messaging.redis_broker import RedisMessageBroker
from app.adapters.persistence.filesystem_repo import FileSystemLexiconRepository
from app.adapters.s3_repo import S3LanguageRepo
from app.adapters.engines.gf_wrapper import GFGrammarEngine
from app.adapters.engines.pidgin_runtime import PidginGrammarEngine
from app.adapters.llm_adapter import GeminiAdapter

# --- Use Cases ---
from app.core.use_cases.generate_text import GenerateText
from app.core.use_cases.build_language import BuildLanguage
from app.core.use_cases.onboard_language_saga import OnboardLanguageSaga

class Container(containers.DeclarativeContainer):
    """
    Dependency Injection Container.
    Acts as the "Switchboard" connecting Adapters to Use Cases.
    """

    # 1. Wiring Configuration
    wiring_config = containers.WiringConfiguration(
        modules=[
            "app.adapters.api.routers.generation",
            "app.adapters.api.routers.management",
            # Removed 'languages' router as it is not wired in main.py
            "app.adapters.api.routers.health",
            "app.adapters.api.dependencies",
        ]
    )

    # 2. Infrastructure Gateways
    
    # Message Broker
    message_broker = providers.Singleton(RedisMessageBroker)

    # Persistence (Selector: S3 vs FileSystem)
    if settings.STORAGE_BACKEND == "s3":
        language_repo = providers.Singleton(S3LanguageRepo)
    else:
        language_repo = providers.Singleton(
            FileSystemLexiconRepository, 
            base_path=settings.FILESYSTEM_REPO_PATH
        )
    
    # Alias so 'health.py' can find 'lexicon_repository'
    lexicon_repository = language_repo

    # Grammar Engine (Fixed: Switched from Selector to if/else)
    if settings.USE_MOCK_GRAMMAR:
        grammar_engine = providers.Singleton(PidginGrammarEngine)
    else:
        grammar_engine = providers.Singleton(GFGrammarEngine, lib_path=settings.GF_LIB_PATH)

    # LLM Client (Gemini BYOK)
    llm_client = providers.Singleton(GeminiAdapter)

    # 3. Use Cases (Application Logic)
    
    generate_text_use_case = providers.Factory(
        GenerateText,
        # Named argument must match GenerateText.__init__(self, engine, ...)
        engine=grammar_engine,
    )

    build_language_use_case = providers.Factory(
        BuildLanguage,
        broker=message_broker
    )

    onboard_language_saga = providers.Factory(
        OnboardLanguageSaga,
        broker=message_broker,
        repo=language_repo 
    )

# Global Container Instance
container = Container()