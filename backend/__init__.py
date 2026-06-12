import logging

from fastapi import APIRouter

from .adapters.base import AssistantAdapter
from .api.deps import set_adapter, set_chat_service, set_tool_registry
from .api.router import router as _ai_router
from .core.chat.service import ChatService
from .core.config import EngineSettings
from .core.database import create_tables, init_database
from .core.llm.factory import create_llm_provider
from .core.tools import ToolRegistry


async def create_assistant_app(
    adapter: AssistantAdapter,
    settings: EngineSettings | None = None,
) -> APIRouter:
    if settings is None:
        settings = EngineSettings()

    ai_logger = logging.getLogger("ai")
    ai_logger.setLevel(logging.INFO)
    if not ai_logger.handlers:
        ai_logger.addHandler(logging.StreamHandler())

    init_database(settings.DATABASE_URL)
    await create_tables()

    llm = create_llm_provider(settings)
    chat_service = ChatService(llm=llm, settings=settings)

    tool_registry = None
    if adapter.tools:
        tool_registry = ToolRegistry()
        tool_registry.register_many(adapter.tools.get_tools())

    set_adapter(adapter)
    set_chat_service(chat_service)
    set_tool_registry(tool_registry)

    return _ai_router
