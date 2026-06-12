import json
import logging
import time
from typing import AsyncGenerator, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import EngineSettings
from ..llm.provider import LLMProvider, Message, StreamChunk, ToolDefinition
from ..tools import ToolRegistry
from .compression import compress_history
from .models import ChatMessage, ChatSession

logger = logging.getLogger("ai.chat")


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
        tool_registry: Optional[ToolRegistry] = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        session = await self.get_session(db, session_id, user_id)
        if not session:
            logger.warning("session not found: %s user=%s", session_id, user_id)
            yield StreamChunk(type="error", content="Session not found")
            return

        logger.info(
            "chat start session=%s user=%s msg=%s",
            session_id, user_id, user_message[:80],
        )
        await self._add_message(db, session, "user", user_message)
        await self._auto_title(db, session, user_message)

        tool_defs = tools
        if not tool_defs and tool_registry:
            tool_defs = tool_registry.get_definitions()

        t_start = time.monotonic()
        round_num = 0
        total_tool_calls = 0

        while True:
            round_num += 1
            messages = self._build_messages(session, system_prompt)
            logger.info("round %d  messages=%d  session=%s", round_num, len(messages), session_id)

            if len(messages) > self.settings.CONTEXT_WINDOW_SIZE:
                messages = await compress_history(
                    messages, self.llm, keep_recent=self.settings.CONTEXT_WINDOW_SIZE
                )

            full_content = ""
            all_tool_calls: list[dict] = []

            try:
                async for chunk in self.llm.generate_stream(
                    messages=messages, tools=tool_defs
                ):
                    if chunk.type == "text":
                        full_content += chunk.content
                        yield chunk
                    elif chunk.type == "tool_call" and chunk.tool_call:
                        all_tool_calls.append(chunk.tool_call)
                        yield chunk
            except Exception:
                logger.exception("LLM stream error session=%s round=%d", session_id, round_num)
                yield StreamChunk(type="error", content="LLM streaming failed")
                return

            await self._add_message(
                db, session, "assistant", full_content,
                tool_calls=all_tool_calls or None,
            )

            if not all_tool_calls or not tool_registry:
                break

            total_tool_calls += len(all_tool_calls)
            for tc in all_tool_calls:
                logger.info("tool call: %s  args=%s  session=%s", tc["name"], str(tc.get("arguments", {}))[:120], session_id)
                yield StreamChunk(
                    type="tool_executing",
                    content=tc["name"],
                    tool_call=tc,
                )
                t_tool = time.monotonic()
                result = await tool_registry.execute(
                    tc["name"], tc.get("arguments", {})
                )
                result_content = result.to_content_string()
                logger.info(
                    "tool result: %s  ok=%s  %.1fs  session=%s",
                    tc["name"], result.success, time.monotonic() - t_tool, session_id,
                )

                await self._add_message(
                    db, session, "tool", result_content,
                    tool_call_id=tc["id"],
                )
                yield StreamChunk(
                    type="tool_result",
                    content=result_content,
                    tool_call={"id": tc["id"], "name": tc["name"]},
                )

        elapsed = time.monotonic() - t_start
        logger.info(
            "chat done session=%s rounds=%d tools=%d %.1fs",
            session_id, round_num, total_tool_calls, elapsed,
        )
        yield StreamChunk(type="done")
        await db.flush()
