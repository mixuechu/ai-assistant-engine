"""Standalone entry point for development and testing."""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .adapters.base import AssistantAdapter, AuthAdapter, UserInfo
from .core.config import EngineSettings

settings = EngineSettings()


class DevAuthAdapter(AuthAdapter):
    """Bypass auth for local development — all requests use a test user."""

    async def verify_token(self, token: str):
        return UserInfo(
            id="dev-user-001",
            username="developer",
            display_name="Dev User",
            permissions=["admin:all"],
        )

    async def get_user_info(self, user_id: str):
        return await self.verify_token("")


app = FastAPI(title="AI Assistant Engine (Dev)", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    from . import create_assistant_app

    adapter = AssistantAdapter(auth=DevAuthAdapter())
    router = await create_assistant_app(adapter=adapter, settings=settings)
    app.include_router(router, prefix="/api/v1/ai")


@app.get("/health")
async def health():
    return {"status": "ok", "engine": "ai-assistant"}


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8001, reload=True)
