from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from typing import Optional

from ..adapters.base import AssistantAdapter, UserInfo
from ..core.chat.service import ChatService
from ..core.database import get_db_session
from ..core.tools import ToolRegistry

_security = HTTPBearer()
_adapter: AssistantAdapter | None = None
_chat_service: ChatService | None = None
_tool_registry: ToolRegistry | None = None


def set_adapter(adapter: AssistantAdapter):
    global _adapter
    _adapter = adapter


def set_chat_service(service: ChatService):
    global _chat_service
    _chat_service = service


def set_tool_registry(registry: Optional[ToolRegistry]):
    global _tool_registry
    _tool_registry = registry


def get_adapter() -> AssistantAdapter:
    if _adapter is None:
        raise RuntimeError("AssistantAdapter not configured")
    return _adapter


def get_chat_service() -> ChatService:
    if _chat_service is None:
        raise RuntimeError("ChatService not configured")
    return _chat_service


def get_tool_registry() -> Optional[ToolRegistry]:
    return _tool_registry


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
    adapter: AssistantAdapter = Depends(get_adapter),
) -> UserInfo:
    user = await adapter.auth.verify_token(credentials.credentials)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


async def get_db(session: AsyncSession = Depends(get_db_session)):
    yield session
