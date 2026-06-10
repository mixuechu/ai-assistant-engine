from fastapi import APIRouter

from .adapters.base import AssistantAdapter
from .api.deps import set_adapter, set_chat_service
from .api.router import router as _ai_router
from .core.chat.service import ChatService
from .core.config import EngineSettings
from .core.database import create_tables, init_database
from .core.llm.factory import create_llm_provider


async def create_assistant_app(
    adapter: AssistantAdapter,
    settings: EngineSettings | None = None,
) -> APIRouter:
    """Initialize the AI assistant engine and return a mountable FastAPI router.

    Usage in host app:
        from ai_assistant_engine.backend import create_assistant_app
        router = await create_assistant_app(adapter=my_adapter)
        app.include_router(router, prefix="/api/v1/ai")
    """
    if settings is None:
        settings = EngineSettings()

    init_database(settings.DATABASE_URL)
    await create_tables()

    llm = create_llm_provider(settings)
    chat_service = ChatService(llm=llm, settings=settings)

    set_adapter(adapter)
    set_chat_service(chat_service)

    return _ai_router
