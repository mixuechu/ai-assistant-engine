import logging
from typing import Optional

from .base import BaseTool, ToolResult
from ..llm.provider import ToolDefinition

logger = logging.getLogger("ai.tools")


class ToolRegistry:

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def register_many(self, tools: list[BaseTool]) -> None:
        for tool in tools:
            self.register(tool)

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def get_definitions(self) -> list[ToolDefinition]:
        return [t.to_definition() for t in self._tools.values()]

    async def execute(self, name: str, arguments: dict) -> ToolResult:
        tool = self._tools.get(name)
        if not tool:
            logger.warning("unknown tool requested: %s", name)
            return ToolResult(success=False, error=f"Unknown tool: {name}")
        try:
            return await tool.execute(**arguments)
        except Exception as e:
            logger.exception("tool %s raised exception", name)
            return ToolResult(success=False, error=str(e))
