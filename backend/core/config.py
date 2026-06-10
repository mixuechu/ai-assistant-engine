from pydantic_settings import BaseSettings
from typing import Optional


class EngineSettings(BaseSettings):
    # LLM
    LLM_PROVIDER: str = "claude"
    ANTHROPIC_API_KEY: Optional[str] = None
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_BASE_URL: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # Engine database
    DATABASE_URL: str = "sqlite+aiosqlite:///./ai_assistant.db"

    # Auth
    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Behavior
    DEBUG: bool = False
    MAX_MESSAGES_PER_SESSION: int = 200
    CONTEXT_WINDOW_SIZE: int = 50
    SYSTEM_PROMPT: str = (
        "You are a helpful AI assistant embedded in a business system. "
        "Answer questions clearly and concisely. "
        "When you don't know something, say so honestly."
    )

    model_config = {"env_prefix": "AI_", "env_file": ".env", "extra": "ignore"}


settings = EngineSettings()
