import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.agent import router as agent_router
from app.api.conversations import router as conversations_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.organization import router as organization_router
from app.api.query import router as query_router
from app.api.tickets import router as tickets_router

app = FastAPI(title="AI Knowledge Agent Platform")

cors_origins = os.getenv(
	"CORS_ORIGINS",
	"http://localhost:5173,http://127.0.0.1:5173",
).split(",")
app.add_middleware(
	CORSMiddleware,
	allow_origins=[origin.strip() for origin in cors_origins if origin.strip()],
	allow_credentials=False,
	allow_methods=["GET", "POST", "OPTIONS"],
	allow_headers=["Authorization", "Content-Type"],
)

app.include_router(health_router)
app.include_router(organization_router)
app.include_router(auth_router)
app.include_router(conversations_router)
app.include_router(documents_router)
app.include_router(query_router)
app.include_router(tickets_router)
app.include_router(agent_router)
