from typing import Callable, Optional

from .auth_adapter import JinhuiErpAuthAdapter
from .tool_provider import JinhuiErpToolProvider
from .sql_runner import JinhuiErpSqlRunner
from .schema import ALLOWED_TABLES, SCHEMA_DESCRIPTION
from ..base import AssistantAdapter
from ...core.nl2sql import SqlValidator, NL2SQLTool, SchemaPromptBuilder


def create_jinhui_erp_adapter(
    jwt_secret: str,
    jwt_algorithm: str = "HS256",
    user_loader: Optional[Callable] = None,
    db_session_factory=None,
) -> AssistantAdapter:
    auth = JinhuiErpAuthAdapter(
        jwt_secret=jwt_secret,
        jwt_algorithm=jwt_algorithm,
        user_loader=user_loader,
    )

    tools = None
    system_prompt = _BASE_SYSTEM_PROMPT

    if db_session_factory:
        tool_provider = JinhuiErpToolProvider()
        sql_runner = JinhuiErpSqlRunner(db_session_factory)
        sql_validator = SqlValidator(allowed_tables=ALLOWED_TABLES)
        nl2sql_tool = NL2SQLTool(sql_runner=sql_runner, sql_validator=sql_validator)
        tool_provider.add_tool(nl2sql_tool)
        tools = tool_provider

        schema_builder = SchemaPromptBuilder(SCHEMA_DESCRIPTION)
        system_prompt = _BASE_SYSTEM_PROMPT + "\n\n" + schema_builder.build_prompt_section()

    return AssistantAdapter(auth=auth, tools=tools, system_prompt=system_prompt)


_BASE_SYSTEM_PROMPT = """你是晋惠钙业生产管理系统的AI助手。你可以查询系统中的业务数据来回答用户的问题。

## 你的能力
- 查询业务数据
- 你有一个 `run_sql` 工具，可以对业务数据库执行 SELECT 查询
- 你应该根据下方提供的数据库 Schema 来编写 SQL

## 行为规范
- 用中文回答
- 只做查询，不做任何数据修改
- 不要编造数据，查不到就如实告知
- SQL 只写 SELECT 语句
- 结果较多时进行汇总，不要原样输出大量数据
- 查询员工时请加 WHERE is_active = true 条件（除非用户明确要求查看离职员工）
- 多租户系统，查询时需限定 tenant_id（从当前用户上下文获取）
- 查询文件时请加 WHERE is_deleted = false 条件
- UUID 类型的 id 在 SQL 中需要用字符串形式比较"""
