from typing import Any

from sqlalchemy import text

from ...core.nl2sql import SqlRunner


class XingERPSqlRunner(SqlRunner):

    def __init__(self, session_factory):
        self._sf = session_factory

    async def run_sql(self, sql: str) -> list[dict[str, Any]]:
        async with self._sf() as db:
            try:
                await db.execute(text("SET statement_timeout = '5000'"))
            except Exception:
                pass
            result = await db.execute(text(sql))
            return [dict(r) for r in result.mappings().all()]
