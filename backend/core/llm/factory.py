from ..config import EngineSettings
from .provider import LLMProvider
from .claude_provider import ClaudeProvider
from .openai_provider import OpenAIProvider
from .deepseek_provider import DeepSeekProvider


def create_llm_provider(settings: EngineSettings) -> LLMProvider:
    provider = settings.LLM_PROVIDER.lower()

    if provider == "claude":
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is required for Claude provider")
        return ClaudeProvider(
            api_key=settings.ANTHROPIC_API_KEY,
            model=settings.CLAUDE_MODEL,
        )

    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required for OpenAI provider")
        return OpenAIProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            base_url=settings.OPENAI_BASE_URL,
        )

    if provider == "deepseek":
        if not settings.DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY is required for DeepSeek provider")
        return DeepSeekProvider(
            api_key=settings.DEEPSEEK_API_KEY,
            model=settings.DEEPSEEK_MODEL,
        )

    raise ValueError(f"Unknown LLM provider: {provider}")
