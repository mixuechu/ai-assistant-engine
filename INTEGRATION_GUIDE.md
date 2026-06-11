# AI Assistant Engine — 集成指南

将 ai-assistant-engine 集成到任意带数据库的 FastAPI 系统中，为其添加 NL2SQL 驱动的 AI 助手。

## 前置条件

- 宿主系统使用 **FastAPI** + **SQLAlchemy (async)**
- 宿主系统有 **JWT 认证**（Bearer token）
- 前端使用 **React** + **TypeScript**
- Python 3.10+

## 架构概览

```
宿主系统 (如 ERP)
├── backend/
│   ├── app/api/v1/ai_assistant.py    ← 集成入口（你写）
│   └── app/main.py                   ← 挂载路由
├── frontend/
│   └── src/components/AiAssistant/   ← 拷贝前端组件
│
ai-assistant-engine/                   ← 独立仓库
├── backend/
│   ├── core/           ← 引擎核心（LLM、聊天、NL2SQL、工具）
│   ├── adapters/
│   │   ├── base.py     ← 适配器接口定义
│   │   └── your_app/   ← 你的适配器（你写）
│   └── __init__.py     ← create_assistant_app()
└── frontend/src/       ← 可复用的 React 组件
```

## 集成步骤

### Step 1: 后端依赖

在宿主系统的 `requirements.txt` 中添加：

```
anthropic>=0.34.0
openai>=1.40.0
sse-starlette>=2.1.0
google-auth>=2.29.0
```

### Step 2: 创建适配器目录

在 ai-assistant-engine 中创建你的适配器：

```
backend/adapters/your_app/
├── __init__.py          # 工厂函数 create_your_app_adapter()
├── auth_adapter.py      # JWT 验证
├── schema.py            # 数据库 schema 描述 + 表白名单
├── sql_runner.py        # SQL 执行器
└── tool_provider.py     # 工具注册
```

#### 2.1 auth_adapter.py — JWT 认证适配

```python
from typing import Callable, Optional
from jose import jwt, JWTError
from ..base import AuthAdapter, UserInfo

class YourAppAuthAdapter(AuthAdapter):
    def __init__(self, jwt_secret: str, jwt_algorithm: str = "HS256",
                 user_loader: Optional[Callable] = None):
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        self.user_loader = user_loader

    async def verify_token(self, token: str) -> Optional[UserInfo]:
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
        except JWTError:
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        if self.user_loader:
            return await self.user_loader(str(user_id))
        return UserInfo(id=str(user_id), username="", display_name="")

    async def get_user_info(self, user_id: str) -> Optional[UserInfo]:
        if self.user_loader:
            return await self.user_loader(user_id)
        return UserInfo(id=user_id, username="", display_name="")
```

**关键点：**
- `payload.get("sub")` — 根据你的 JWT 结构调整 claim 名称
- `payload.get("type") != "access"` — 如果你的 JWT 有 type 字段，加上验证
- `user_loader` — 可选回调，用于从宿主数据库加载完整用户信息

#### 2.2 schema.py — 数据库 Schema 描述

这是最重要的一步。你需要为 LLM 描述你的数据库结构。

```python
# 表白名单 — 只有这些表允许被查询
ALLOWED_TABLES = [
    "users", "orders", "products", "categories",
    # 不要包含：passwords, sessions, api_keys 等敏感表
]

# Schema 描述 — LLM 据此生成 SQL
SCHEMA_DESCRIPTION = {
    "users": {
        "description": "用户表",
        "columns": [
            {"name": "id", "type": "INTEGER", "description": "主键"},
            {"name": "name", "type": "VARCHAR(100)", "description": "用户名"},
            {"name": "email", "type": "VARCHAR(200)", "description": "邮箱"},
            {"name": "created_at", "type": "TIMESTAMP", "description": "注册时间"},
            {"name": "is_active", "type": "BOOLEAN", "description": "是否激活"},
        ],
    },
    "orders": {
        "description": "订单表",
        "columns": [
            {"name": "id", "type": "INTEGER", "description": "主键"},
            {"name": "user_id", "type": "INTEGER FK→users", "description": "下单用户"},
            {"name": "total_amount", "type": "DECIMAL(10,2)", "description": "订单金额"},
            {"name": "status", "type": "VARCHAR(20)", "description": "状态: pending/paid/shipped/completed"},
            {"name": "created_at", "type": "TIMESTAMP", "description": "下单时间"},
        ],
    },
    # ... 更多表
}
```

**Schema 描述最佳实践：**
- 字段类型写清楚，特别是 FK 关系（如 `FK→users`）
- 枚举值写出来（如 `状态: pending/paid/shipped`）
- 用中文写 description（或用户的母语）
- Boolean 字段说明含义（如 `是否已删除（查询时请加 is_deleted=false）`）
- 敏感列不要写进 schema（password_hash、api_key 等）
- 敏感表不要加到 ALLOWED_TABLES（permissions、sessions 等）

#### 2.3 sql_runner.py — SQL 执行器

```python
from typing import Any
from sqlalchemy import text
from ...core.nl2sql import SqlRunner

class YourAppSqlRunner(SqlRunner):
    def __init__(self, session_factory):
        self._sf = session_factory

    async def run_sql(self, sql: str) -> list[dict[str, Any]]:
        async with self._sf() as db:
            try:
                # PostgreSQL 超时保护（SQLite 不支持，会自动跳过）
                await db.execute(text("SET statement_timeout = '5000'"))
            except Exception:
                pass
            result = await db.execute(text(sql))
            return [dict(r) for r in result.mappings().all()]
```

**关键点：**
- `session_factory` 是宿主系统的 `AsyncSessionLocal`
- 建议使用**只读数据库连接**（生产环境）
- `SET statement_timeout` 防止慢查询（PostgreSQL only）

#### 2.4 tool_provider.py — 工具注册

```python
from ..base import ToolProvider

class YourAppToolProvider(ToolProvider):
    def __init__(self):
        self._tools = []

    def add_tool(self, tool):
        self._tools.append(tool)

    def get_tools(self):
        return list(self._tools)
```

#### 2.5 __init__.py — 适配器工厂函数

```python
from typing import Callable, Optional
from .auth_adapter import YourAppAuthAdapter
from .tool_provider import YourAppToolProvider
from .sql_runner import YourAppSqlRunner
from .schema import ALLOWED_TABLES, SCHEMA_DESCRIPTION
from ..base import AssistantAdapter
from ...core.nl2sql import SqlValidator, NL2SQLTool, SchemaPromptBuilder

def create_your_app_adapter(
    jwt_secret: str,
    jwt_algorithm: str = "HS256",
    user_loader: Optional[Callable] = None,
    db_session_factory=None,
) -> AssistantAdapter:
    auth = YourAppAuthAdapter(
        jwt_secret=jwt_secret, jwt_algorithm=jwt_algorithm, user_loader=user_loader,
    )

    tools = None
    system_prompt = _BASE_SYSTEM_PROMPT

    if db_session_factory:
        tool_provider = YourAppToolProvider()
        sql_runner = YourAppSqlRunner(db_session_factory)
        sql_validator = SqlValidator(allowed_tables=ALLOWED_TABLES)
        nl2sql_tool = NL2SQLTool(sql_runner=sql_runner, sql_validator=sql_validator)
        tool_provider.add_tool(nl2sql_tool)
        tools = tool_provider

        schema_builder = SchemaPromptBuilder(SCHEMA_DESCRIPTION)
        system_prompt = _BASE_SYSTEM_PROMPT + "\n\n" + schema_builder.build_prompt_section()

    return AssistantAdapter(auth=auth, tools=tools, system_prompt=system_prompt)

_BASE_SYSTEM_PROMPT = """你是[系统名称]的AI助手。你可以查询系统中的业务数据来回答用户的问题。

## 你的能力
- 查询业务数据（用户、订单、产品等）
- 你有一个 `run_sql` 工具，可以对业务数据库执行 SELECT 查询
- 你应该根据下方提供的数据库 Schema 来编写 SQL

## 行为规范
- 用中文回答
- 只做查询，不做任何数据修改
- 不要编造数据，查不到就如实告知
- SQL 只写 SELECT 语句
- 结果较多时进行汇总，不要原样输出大量数据"""
```

### Step 3: 宿主系统后端集成

在宿主系统中创建路由文件：

```python
# backend/app/api/v1/ai_assistant.py
import sys, os
from pathlib import Path

# 将 ai-assistant-engine 加入 Python 路径
_engine_path = Path(__file__).resolve().parents[5] / "ai-assistant-engine"
if str(_engine_path) not in sys.path:
    sys.path.insert(0, str(_engine_path))

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings as app_settings
from app.core.database import AsyncSessionLocal
from app.models.user import User              # 你的用户模型

from backend.adapters.base import UserInfo
from backend.adapters.your_app import create_your_app_adapter
from backend.core.config import EngineSettings
from backend import create_assistant_app


async def _load_user(user_id: str) -> UserInfo | None:
    """从宿主数据库加载用户信息。"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return None
        return UserInfo(
            id=str(user.id),
            username=user.username or "",
            display_name=user.display_name or "",
            permissions=[],    # 可根据需要填充
            metadata={},
        )


async def create_ai_router() -> APIRouter:
    adapter = create_your_app_adapter(
        jwt_secret=app_settings.SECRET_KEY,
        jwt_algorithm=app_settings.ALGORITHM,
        user_loader=_load_user,
        db_session_factory=AsyncSessionLocal,
    )

    ai_settings = EngineSettings(
        LLM_PROVIDER=os.getenv("AI_LLM_PROVIDER", "deepseek"),
        DEEPSEEK_API_KEY=os.getenv("DEEPSEEK_API_KEY"),
        DATABASE_URL=os.getenv("AI_DATABASE_URL", "sqlite+aiosqlite:///./ai_assistant.db"),
        JWT_SECRET=app_settings.SECRET_KEY,
        JWT_ALGORITHM=app_settings.ALGORITHM,
    )

    return await create_assistant_app(adapter=adapter, settings=ai_settings)
```

在 `main.py` 中挂载路由：

```python
async def lifespan(app: FastAPI):
    # ... 你的初始化代码 ...

    # AI Assistant
    try:
        from app.api.v1.ai_assistant import create_ai_router
        ai_router = await create_ai_router()
        app.include_router(ai_router, prefix="/api/v1/ai", tags=["AI助手"])
        logger.info("AI助手模块已加载")
    except Exception as e:
        logger.warning(f"AI助手模块加载失败（非致命）: {e}")

    yield
```

### Step 4: 前端集成

将前端组件拷贝到宿主系统：

```bash
# 从 ai-assistant-engine 拷贝
cp -r ai-assistant-engine/frontend/src/components/* your-app/src/components/AiAssistant/
cp ai-assistant-engine/frontend/src/types.ts your-app/src/components/AiAssistant/types.ts
cp ai-assistant-engine/frontend/src/hooks/useChat.ts your-app/src/components/AiAssistant/useChat.ts
cp ai-assistant-engine/frontend/src/styles/assistant.css your-app/src/components/AiAssistant/assistant.css
```

修复导入路径（从 `../types` 改为 `./types` 等）。

在布局组件中使用：

```tsx
import { AiAssistant } from '../components/AiAssistant'

// 在 Layout 的 return 中加入：
<AiAssistant
  endpoint="/api/v1/ai"
  title="AI 助手"
  placeholder="问我任何关于系统的问题..."
  welcomeMessage="你好！我是系统的AI助手，有什么可以帮你？"
/>
```

如果前端开发服务器和后端不在同一端口，配置 proxy：

```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
},
```

### Step 5: 环境变量

```env
# LLM 选择 — 支持: claude | claude-vertex | openai | deepseek
AI_LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-key

# 或者用 Claude (直接 API)
# AI_LLM_PROVIDER=claude
# ANTHROPIC_API_KEY=sk-ant-your-key

# 或者用 Claude (Vertex AI)
# AI_LLM_PROVIDER=claude-vertex
# GOOGLE_CLOUD_PROJECT=your-project-id
# ANTHROPIC_VERTEX_REGION=us-east5

# AI 引擎会话数据库（独立于宿主系统数据库）
AI_DATABASE_URL=sqlite+aiosqlite:///./ai_assistant.db
```

## 安全层

NL2SQL 的安全由三层保护：

1. **System Prompt 层** — 指导 LLM 只写 SELECT，不做数据修改
2. **SqlValidator 层** — 硬编码规则：
   - 只允许 SELECT 开头的语句
   - 拒绝 INSERT/UPDATE/DELETE/DROP/ALTER 等关键字
   - 表白名单过滤（不在 ALLOWED_TABLES 的表一律拒绝）
   - 自动添加 LIMIT（默认 100 行）
   - 拒绝多语句（`;` 分割）
3. **数据库层** — 建议生产环境使用只读连接

## 测试验证

集成后的验证清单：

- [ ] 登录获取 JWT → 发送聊天消息 → 收到 SSE 流式响应
- [ ] 简单查询（如"有多少用户"）→ 生成正确 SQL → 返回数据
- [ ] 复杂查询（JOIN、GROUP BY、子查询）→ 正确执行
- [ ] 危险操作请求（如"删除所有数据"）→ 被拒绝
- [ ] 查询敏感表 → 被白名单拦截
- [ ] SQL 注入尝试 → 被 Validator 拦截
- [ ] 多轮对话 → 会话上下文保持
- [ ] 工具执行状态 → 前端显示"正在查询..."和"完成"

## 自定义要点

| 自定义项 | 文件 | 说明 |
|---------|------|------|
| 系统人设 | `__init__.py` 中的 `_BASE_SYSTEM_PROMPT` | 调整 AI 的角色和行为规范 |
| 可查询的表 | `schema.py` 中的 `ALLOWED_TABLES` | 控制安全边界 |
| Schema 描述 | `schema.py` 中的 `SCHEMA_DESCRIPTION` | 影响 SQL 生成准确率 |
| LLM 模型 | 环境变量 `AI_LLM_PROVIDER` | 支持 Claude/OpenAI/DeepSeek |
| 行数限制 | `SqlValidator(max_rows=100)` | 防止大结果集 |
| JWT 格式 | `auth_adapter.py` | 适配你的 token 结构 |
| 前端样式 | `assistant.css` | CSS 变量控制配色 |

## 测试结果参考（XingERP 集成）

| 模型 | 正常查询 | 安全拦截 | 总计 | 备注 |
|------|---------|---------|------|------|
| Claude Sonnet 4.6 (Vertex) | 10/10 | 4/4 | 100% | Q8/Q10 通过 agentic loop 自动修正 |
| DeepSeek Chat | 10/10 | 4/4 | 100% | 表现与 Claude 一致 |

两个模型在相同的 schema 描述下生成的 SQL 质量几乎一致。Agentic loop（最多 5 轮工具调用）可以自动修正 SQL 方言差异（如 PostgreSQL 的 TO_CHAR → SQLite 的 STRFTIME）。
