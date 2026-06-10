import re
from typing import Optional


_DANGEROUS_KEYWORDS = re.compile(
    r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|EXEC|EXECUTE|CALL|INTO\s+OUTFILE|LOAD\s+DATA)\b',
    re.IGNORECASE,
)

_TABLE_PATTERN = re.compile(
    r'\bFROM\s+(\w+)|\bJOIN\s+(\w+)',
    re.IGNORECASE,
)

_LIMIT_PATTERN = re.compile(r'\bLIMIT\s+\d+', re.IGNORECASE)

_SEMICOLON_SPLIT = re.compile(r';\s*(?=\S)')


class SqlValidator:

    def __init__(
        self,
        allowed_tables: list[str],
        max_rows: int = 100,
        timeout_ms: int = 5000,
    ):
        self.allowed_tables = {t.lower() for t in allowed_tables}
        self.max_rows = max_rows
        self.timeout_ms = timeout_ms

    def validate(self, sql: str) -> tuple[bool, Optional[str]]:
        sql_stripped = sql.strip().rstrip(';')

        if _SEMICOLON_SPLIT.search(sql_stripped):
            return False, "不允许执行多条SQL语句"

        if not sql_stripped.upper().lstrip().startswith('SELECT'):
            return False, "只允许执行 SELECT 查询"

        match = _DANGEROUS_KEYWORDS.search(sql_stripped)
        if match:
            return False, f"SQL 包含不允许的操作: {match.group(0)}"

        tables = self._extract_tables(sql_stripped)
        for table in tables:
            if table.lower() not in self.allowed_tables:
                return False, f"不允许查询表: {table}"

        return True, None

    def enforce_limit(self, sql: str) -> str:
        sql_stripped = sql.strip().rstrip(';')
        if not _LIMIT_PATTERN.search(sql_stripped):
            sql_stripped += f' LIMIT {self.max_rows}'
        return sql_stripped

    def _extract_tables(self, sql: str) -> list[str]:
        tables = []
        for match in _TABLE_PATTERN.finditer(sql):
            table = match.group(1) or match.group(2)
            if table:
                tables.append(table)
        return tables
