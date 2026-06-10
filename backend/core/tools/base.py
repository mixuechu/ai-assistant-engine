import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from ..llm.provider import ToolDefinition


@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: Optional[str] = None

    def to_content_string(self) -> str:
        if not self.success:
            return json.dumps({"error": self.error}, ensure_ascii=False)
        return json.dumps(self.data, ensure_ascii=False, default=str)


class BaseTool(ABC):

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]: ...

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult: ...

    def to_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
        )
