from typing import Callable, Optional

from .auth_adapter import XingERPAuthAdapter
from .tool_provider import XingERPToolProvider
from .sql_runner import XingERPSqlRunner
from .schema import ALLOWED_TABLES, SCHEMA_DESCRIPTION
from ..base import AssistantAdapter
from ...core.nl2sql import SqlValidator, NL2SQLTool, SchemaPromptBuilder


def create_xing_erp_adapter(
    jwt_secret: str,
    jwt_algorithm: str = "HS256",
    user_loader: Optional[Callable] = None,
    db_session_factory=None,
) -> AssistantAdapter:
    auth = XingERPAuthAdapter(
        jwt_secret=jwt_secret,
        jwt_algorithm=jwt_algorithm,
        user_loader=user_loader,
    )

    tools = None
    system_prompt = _BASE_SYSTEM_PROMPT

    if db_session_factory:
        tool_provider = XingERPToolProvider()

        sql_runner = XingERPSqlRunner(db_session_factory)
        sql_validator = SqlValidator(allowed_tables=ALLOWED_TABLES)
        nl2sql_tool = NL2SQLTool(sql_runner=sql_runner, sql_validator=sql_validator)
        tool_provider.add_tool(nl2sql_tool)

        tools = tool_provider

        schema_builder = SchemaPromptBuilder(SCHEMA_DESCRIPTION)
        system_prompt = _BASE_SYSTEM_PROMPT + "\n\n" + schema_builder.build_prompt_section()

    return AssistantAdapter(
        auth=auth,
        tools=tools,
        system_prompt=system_prompt,
    )


_BASE_SYSTEM_PROMPT = """你是星鑫财税ERP系统的AI助手。你可以查询系统中的业务数据来回答用户的问题。

## 你的能力
- 查询客户信息、工单状态、费用情况、员工信息、工作流进度等
- 你有一个 `run_sql` 工具，可以对业务数据库执行 SELECT 查询
- 你应该根据下方提供的数据库 Schema 来编写 SQL

## 行为规范
- 用中文回答
- 只做查询，不做任何数据修改
- 查询 customers 表时请加 `WHERE is_deleted = false` 条件
- 不要编造数据，查不到就如实告知
- SQL 只写 SELECT 语句，不要写 INSERT/UPDATE/DELETE
- 结果较多时进行汇总，不要原样输出大量数据"""
