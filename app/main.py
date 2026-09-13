from fastapi import FastAPI

from app.api.health import router as health_router

app = FastAPI(title="AI Knowledge Agent Platform")

app.include_router(health_router)
