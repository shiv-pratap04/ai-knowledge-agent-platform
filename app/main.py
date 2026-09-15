from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.agent import router as agent_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.query import router as query_router

app = FastAPI(title="AI Knowledge Agent Platform")

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(query_router)
app.include_router(agent_router)
