from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import ROOT_DIR
from .core.errors import register_exception_handlers
from .core.logging import setup_logging
from .core.middleware import request_log_middleware
from .database import init_db, should_auto_init_db
from .infrastructure import get_infrastructure_status
from .redis_client import get_redis_health
from .routes import (
    admin,
    agent,
    application_profiles,
    auth,
    history,
    interview,
    langgraph_agent,
    memory,
    position_agent,
    rag,
    rag_documents,
    resume,
    training,
)

setup_logging()

app = FastAPI(title="AI Mock Interview System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(request_log_middleware)
register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(agent.router)
app.include_router(langgraph_agent.router)
app.include_router(application_profiles.router)
app.include_router(interview.router)
app.include_router(resume.router)
app.include_router(history.router)
app.include_router(rag.router)
app.include_router(rag_documents.router)
app.include_router(memory.router)
app.include_router(position_agent.router)
app.include_router(training.router)
if should_auto_init_db():
    init_db()

app.mount("/static", StaticFiles(directory=ROOT_DIR), name="static")


@app.get("/api/health")
async def health_check() -> dict:
    return {
        "status": "ok",
        "service": "ai-mock-interview-system",
        "redis": get_redis_health(),
        "infrastructure": get_infrastructure_status(),
    }


@app.get("/styles.css")
async def styles() -> FileResponse:
    return FileResponse(ROOT_DIR / "styles.css", media_type="text/css")


@app.get("/app.js")
async def app_script() -> FileResponse:
    return FileResponse(ROOT_DIR / "app.js", media_type="application/javascript")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(ROOT_DIR / "index.html")
