from typing import Any, Callable, Optional

from .auth import JWTAuthAdapter
from .sql_runner import SQLAlchemySqlRunner
from .tool_provider import SimpleToolProvider
from ...adapters.base import AssistantAdapter
from ...core.nl2sql import SqlValidator, NL2SQLTool, SchemaPromptBuilder


def create_fastapi_adapter(
    jwt_secret: str,
    jwt_algorithm: str = "HS256",
    user_loader: Optional[Callable] = None,
    db_session_factory=None,
    allowed_tables: Optional[list[str]] = None,
    schema_description: Optional[dict[str, Any]] = None,
    system_prompt: str = "You are a helpful AI assistant.",
) -> AssistantAdapter:
    auth = JWTAuthAdapter(
        jwt_secret=jwt_secret,
        jwt_algorithm=jwt_algorithm,
        user_loader=user_loader,
    )

    tools = None
    final_prompt = system_prompt

    if db_session_factory and allowed_tables and schema_description:
        tool_provider = SimpleToolProvider()
        sql_runner = SQLAlchemySqlRunner(db_session_factory)
        sql_validator = SqlValidator(allowed_tables=allowed_tables)
        nl2sql_tool = NL2SQLTool(sql_runner=sql_runner, sql_validator=sql_validator)
        tool_provider.add_tool(nl2sql_tool)
        tools = tool_provider

        schema_builder = SchemaPromptBuilder(schema_description)
        final_prompt = system_prompt + "\n\n" + schema_builder.build_prompt_section()

    return AssistantAdapter(auth=auth, tools=tools, system_prompt=final_prompt)
