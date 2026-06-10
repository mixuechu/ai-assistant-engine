# AI Assistant Engine

Pluggable AI assistant engine for existing business systems.

**Core + Adapter architecture** — the engine handles chat, streaming, sessions, and LLM orchestration. You write a thin adapter for your system's auth, permissions, and data.

## Quick Start

### Embedded in a FastAPI app (recommended)

```python
from ai_assistant_engine.backend import create_assistant_app
from ai_assistant_engine.backend.adapters.xing_erp import create_xing_erp_adapter

adapter = create_xing_erp_adapter(jwt_secret=settings.SECRET_KEY)
router = await create_assistant_app(adapter=adapter)
app.include_router(router, prefix="/api/v1/ai")
```

### Frontend

```tsx
import { AiAssistant } from 'ai-assistant-engine/frontend'

<AiAssistant endpoint="/api/v1/ai" title="AI Assistant" />
```

## Supported LLM Providers

- Claude (Anthropic)
- OpenAI / GPT
- DeepSeek

Set `AI_LLM_PROVIDER` and the corresponding API key in `.env`.

## Writing an Adapter

See `backend/adapters/base.py` for the interface contracts:

- `AuthAdapter` — verify tokens, get user info
- `PermissionAdapter` — control data access per user
- `SchemaAdapter` — describe your database for NL2SQL
- `KnowledgeAdapter` — provide documents for RAG
- `ToolProvider` — register custom tools

Only `AuthAdapter` is required. The rest are optional.

## License

Private — All rights reserved.
