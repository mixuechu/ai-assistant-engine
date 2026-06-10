from typing import Any


class SchemaPromptBuilder:
    """Builds a database schema description section for the LLM system prompt."""

    def __init__(self, schema: dict[str, Any]):
        self._schema = schema

    def build_prompt_section(self) -> str:
        lines = ["## 数据库 Schema", ""]
        for table_name, table_info in self._schema.items():
            desc = table_info.get("description", "")
            lines.append(f"### {table_name}" + (f" — {desc}" if desc else ""))
            columns = table_info.get("columns", [])
            for col in columns:
                col_name = col["name"]
                col_type = col.get("type", "")
                col_desc = col.get("description", "")
                line = f"- `{col_name}`"
                if col_type:
                    line += f" ({col_type})"
                if col_desc:
                    line += f" — {col_desc}"
                lines.append(line)
            lines.append("")
        return "\n".join(lines)
