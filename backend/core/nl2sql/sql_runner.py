from abc import ABC, abstractmethod
from typing import Any


class SqlRunner(ABC):
    """Abstraction for executing SQL against a database."""

    @abstractmethod
    async def run_sql(self, sql: str) -> list[dict[str, Any]]:
        """Execute a SQL query and return rows as list of dicts."""
        ...
