import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.orm import relationship

from ..database import Base, GUID


def _utcnow():
    return datetime.now(timezone.utc)


class ChatSession(Base):
    __tablename__ = "ai_chat_sessions"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    title = Column(String(200), default="New Chat")
    model = Column(String(100), nullable=True)
    message_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.seq",
    )

    __table_args__ = (
        Index("ix_ai_sessions_user_updated", "user_id", "updated_at"),
    )


class ChatMessage(Base):
    __tablename__ = "ai_chat_messages"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(
        GUID(), ForeignKey("ai_chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    seq = Column(Integer, nullable=False)
    role = Column(String(20), nullable=False)  # user | assistant | system | tool
    content = Column(Text, nullable=False, default="")
    tool_calls_json = Column(Text, nullable=True)
    tool_call_id = Column(String(100), nullable=True)
    token_count = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    session = relationship("ChatSession", back_populates="messages")

    __table_args__ = (
        Index("ix_ai_messages_session_seq", "session_id", "seq"),
    )
