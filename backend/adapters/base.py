from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class UserInfo:
    """Host-system-agnostic user representation."""
    id: str
    username: str
    display_name: str
    permissions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Document:
    """A document for RAG indexing."""
    id: str
    title: str
    content: str
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    access_tags: list[str] = field(default_factory=list)


class AuthAdapter(ABC):
    """Authenticates requests using the host system's auth mechanism."""

    @abstractmethod
    async def verify_token(self, token: str) -> Optional[UserInfo]:
        """Verify a bearer token and return user info, or None if invalid."""
        ...

    @abstractmethod
    async def get_user_info(self, user_id: str) -> Optional[UserInfo]:
        """Look up a user by ID."""
        ...


class PermissionAdapter(ABC):
    """Controls what data and tools the AI can access per user."""

    @abstractmethod
    async def get_allowed_tables(self, user: UserInfo) -> list[str]:
        """Tables this user's AI queries can touch."""
        ...

    @abstractmethod
    async def get_allowed_columns(self, user: UserInfo, table: str) -> list[str]:
        """Columns within a table this user can see. Empty = all."""
        ...

    @abstractmethod
    async def get_allowed_tools(self, user: UserInfo) -> list[str]:
        """Tool names this user is allowed to invoke."""
        ...

    @abstractmethod
    async def filter_rag_tags(self, user: UserInfo) -> list[str]:
        """Access tags for RAG document filtering."""
        ...


class SchemaAdapter(ABC):
    """Describes the host system's business database for NL2SQL."""

    @abstractmethod
    async def get_schema_description(self) -> dict[str, Any]:
        """Return structured schema: tables, columns, relations, business meanings."""
        ...

    @abstractmethod
    async def get_database_url(self) -> str:
        """Connection string to the host's business database (read-only recommended)."""
        ...

    @abstractmethod
    async def get_sensitive_columns(self) -> dict[str, list[str]]:
        """Columns that need masking: {table_name: [col1, col2]}."""
        ...


class KnowledgeAdapter(ABC):
    """Provides documents for RAG indexing."""

    @abstractmethod
    async def get_documents(self) -> list[Document]:
        """Return all documents to be indexed."""
        ...


class ToolProvider(ABC):
    """Registers host-system-specific tools for the AI to call."""

    @abstractmethod
    def get_tools(self) -> list[Any]:
        """Return a list of BaseTool instances for registration."""
        ...


class AssistantAdapter:
    """Composite adapter — bundles all adapter interfaces for a host system.

    Subclass this and override the adapters you need. Only auth is required;
    the rest default to permissive/empty stubs.
    """

    def __init__(
        self,
        auth: AuthAdapter,
        permissions: Optional[PermissionAdapter] = None,
        schema: Optional[SchemaAdapter] = None,
        knowledge: Optional[KnowledgeAdapter] = None,
        tools: Optional[ToolProvider] = None,
        system_prompt: Optional[str] = None,
    ):
        self.auth = auth
        self.permissions = permissions
        self.schema = schema
        self.knowledge = knowledge
        self.tools = tools
        self.system_prompt = system_prompt
