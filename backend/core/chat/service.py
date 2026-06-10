import json
from typing import AsyncGenerator, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import EngineSettings
from ..llm.provider import LLMProvider, Message, StreamChunk, ToolDefinition
from .compression import compress_history
from .models import ChatMessage, ChatSession


class ChatService:

    def __init__(self, llm: LLMProvider, settings: EngineSettings):
        self.llm = llm
        self.settings = settings

    async def create_session(
        self, db: AsyncSession, user_id: str, title: str = "New Chat"
    ) -> ChatSession:
        session = ChatSession(user_id=user_id, title=title)
        db.add(session)
        await db.flush()
        return session

    async def get_session(
        self, db: AsyncSession, session_id: str, user_id: str
    ) -> Optional[ChatSession]:
        result = await db.execute(
            select(ChatSession)
            .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .options(selectinload(ChatSession.messages))
        )
        return result.scalar_one_or_none()

    async def list_sessions(
        self, db: AsyncSession, user_id: str, limit: int = 50, offset: int = 0
    ) -> list[ChatSession]:
        result = await db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete_session(
        self, db: AsyncSession, session_id: str, user_id: str
    ) -> bool:
        session = await self.get_session(db, session_id, user_id)
        if not session:
            return False
        await db.delete(session)
        return True

    async def rename_session(
        self, db: AsyncSession, session_id: str, user_id: str, title: str
    ) -> Optional[ChatSession]:
        session = await self.get_session(db, session_id, user_id)
        if not session:
            return None
        session.title = title
        return session

    def _build_messages(
        self,
        session: ChatSession,
        system_prompt: Optional[str] = None,
    ) -> list[Message]:
        messages: list[Message] = []

        prompt = system_prompt or self.settings.SYSTEM_PROMPT
        messages.append(Message(role="system", content=prompt))

        for msg in session.messages:
            tool_calls = []
            if msg.tool_calls_json:
                try:
                    tool_calls = json.loads(msg.tool_calls_json)
                except json.JSONDecodeError:
                    pass
            messages.append(Message(
                role=msg.role,
                content=msg.content,
                tool_calls=tool_calls,
                tool_call_id=msg.tool_call_id,
            ))

        return messages

    async def _add_message(
        self, db: AsyncSession, session: ChatSession, role: str, content: str,
        tool_calls: Optional[list] = None, tool_call_id: Optional[str] = None,
    ) -> ChatMessage:
        session.message_count = (session.message_count or 0) + 1
        msg = ChatMessage(
            seq=session.message_count,
            role=role,
            content=content,
            tool_calls_json=json.dumps(tool_calls, ensure_ascii=False) if tool_calls else None,
            tool_call_id=tool_call_id,
            token_count=self.llm.count_tokens(content),
        )
        session.messages.append(msg)
        return msg

    async def _auto_title(self, db: AsyncSession, session: ChatSession, user_message: str):
        if session.message_count > 1 or session.title != "New Chat":
            return
        title = user_message[:50].strip()
        if len(user_message) > 50:
            title += "..."
        session.title = title

    async def chat_stream(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: str,
        user_message: str,
        system_prompt: Optional[str] = None,
        tools: Optional[list[ToolDefinition]] = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        session = await self.get_session(db, session_id, user_id)
        if not session:
            yield StreamChunk(type="error", content="Session not found")
            return

        await self._add_message(db, session, "user", user_message)
        await self._auto_title(db, session, user_message)

        messages = self._build_messages(session, system_prompt)

        if len(messages) > self.settings.CONTEXT_WINDOW_SIZE:
            messages = await compress_history(
                messages, self.llm, keep_recent=self.settings.CONTEXT_WINDOW_SIZE
            )

        full_content = ""
        all_tool_calls: list[dict] = []

        async for chunk in self.llm.generate_stream(
            messages=messages, tools=tools
        ):
            if chunk.type == "text":
                full_content += chunk.content
            elif chunk.type == "tool_call" and chunk.tool_call:
                all_tool_calls.append(chunk.tool_call)
            yield chunk

        await self._add_message(
            db, session, "assistant", full_content,
            tool_calls=all_tool_calls or None,
        )
        await db.flush()
