from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class SessionResponse(BaseModel):
    id: str
    title: str
    message_count: int
    model: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    tool_calls_json: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RenameRequest(BaseModel):
    title: str
