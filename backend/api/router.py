import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from ..adapters.base import UserInfo
from ..core.chat.service import ChatService
from .deps import get_chat_service, get_current_user, get_db
from .schemas import ChatRequest, MessageResponse, RenameRequest, SessionResponse

router = APIRouter(tags=["ai-assistant"])


@router.post("/chat")
async def chat(
    req: ChatRequest,
    user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service),
):
    session_id = req.session_id
    if not session_id:
        session = await chat_service.create_session(db, user.id)
        session_id = session.id
        await db.flush()

    async def event_generator():
        yield {"event": "session", "data": json.dumps({"session_id": session_id})}

        async for chunk in chat_service.chat_stream(
            db=db,
            session_id=session_id,
            user_id=user.id,
            user_message=req.message,
        ):
            if chunk.type == "text":
                yield {"event": "text", "data": chunk.content}
            elif chunk.type == "tool_call":
                yield {
                    "event": "tool_call",
                    "data": json.dumps(chunk.tool_call, ensure_ascii=False),
                }
            elif chunk.type == "error":
                yield {"event": "error", "data": chunk.content}
            elif chunk.type == "done":
                yield {"event": "done", "data": ""}

    return EventSourceResponse(event_generator())


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    limit: int = 50,
    offset: int = 0,
    user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service),
):
    return await chat_service.list_sessions(db, user.id, limit, offset)


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service),
):
    session = await chat_service.get_session(db, session_id, user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    session_id: str,
    user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service),
):
    session = await chat_service.get_session(db, session_id, user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.messages


@router.put("/sessions/{session_id}/title", response_model=SessionResponse)
async def rename_session(
    session_id: str,
    req: RenameRequest,
    user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service),
):
    session = await chat_service.rename_session(db, session_id, user.id, req.title)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user: UserInfo = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    chat_service: ChatService = Depends(get_chat_service),
):
    deleted = await chat_service.delete_session(db, session_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted"}
