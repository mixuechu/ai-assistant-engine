from typing import Any

from ..tools.base import BaseTool, ToolResult
from .sql_runner import SqlRunner
from .security import SqlValidator


class NL2SQLTool(BaseTool):

    def __init__(self, sql_runner: SqlRunner, sql_validator: SqlValidator):
        self._runner = sql_runner
        self._validator = sql_validator

    @property
    def name(self) -> str:
        return "run_sql"

    @property
    def description(self) -> str:
        return (
            "对业务数据库执行 SQL 查询。只允许 SELECT 语句。"
            "用于回答需要灵活查询数据库的问题，比如统计、筛选、排序、聚合等。"
            "请根据 system prompt 中提供的数据库 schema 来编写 SQL。"
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "要执行的 SELECT SQL 查询语句",
                },
            },
            "required": ["sql"],
        }

    async def execute(self, sql: str, **_kw) -> ToolResult:
        is_valid, error = self._validator.validate(sql)
        if not is_valid:
            return ToolResult(success=False, error=error)

        safe_sql = self._validator.enforce_limit(sql)

        try:
            rows = await self._runner.run_sql(safe_sql)
        except Exception as e:
            return ToolResult(success=False, error=f"SQL 执行错误: {e}")

        return ToolResult(success=True, data={
            "row_count": len(rows),
            "rows": rows,
        })
