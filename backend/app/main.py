"""
DCBrain — FastAPI Application Entry Point
The Autonomous AI Project Manager for Data Centre Construction.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.dependencies import close_neo4j, close_redis

from app.api.routes import dashboard, digital_twin, compliance, commissioning, knowledge, graph
from app.api.websockets import cascade


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle management."""
    # Startup
    print("🧠 DCBrain starting up...")
    await init_db()
    print("✅ PostgreSQL connected")
    print("✅ All systems ready")
    yield
    # Shutdown
    print("🧠 DCBrain shutting down...")
    await close_db()
    await close_neo4j()
    await close_redis()
    print("👋 Goodbye")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="The Autonomous AI Project Manager for Data Centre Construction",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ─────────────────────────────────────────────────────────────

app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(digital_twin.router, prefix="/api/digital-twin", tags=["Digital Twin"])
app.include_router(compliance.router, prefix="/api/compliance", tags=["Compliance"])
app.include_router(commissioning.router, prefix="/api/commissioning", tags=["Commissioning"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["Knowledge"])
app.include_router(graph.router, prefix="/api/graph", tags=["Graph"])
app.include_router(cascade.router)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
