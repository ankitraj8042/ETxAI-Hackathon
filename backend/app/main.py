"""
DCBrain — FastAPI Application Entry Point
The Autonomous AI Project Manager for Data Centre Construction.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.dependencies import close_neo4j, close_redis

from app.api.routes import dashboard, digital_twin, compliance, commissioning, knowledge, graph
from app.api.routes import schedule as schedule_routes
from app.api.routes import supply_chain as supply_chain_routes
from app.api.websockets import cascade
from app.core.logging_config import setup_logging, get_logger

logger = get_logger("dcbrain.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle management."""
    # Startup
    setup_logging()
    logger.info("🧠 DCBrain starting up...")
    await init_db()
    logger.info("✅ Database connected")

    # Initialize graph client (loads in-memory fallback if Neo4j unavailable)
    from app.graph.neo4j_client import graph_client
    await graph_client.initialize()

    # Initialize all AI agents and subscribe to cascade bus events
    from app.agents.orchestrator import orchestrator
    orchestrator.initialize_agents()

    logger.info("✅ All systems ready")
    yield
    # Shutdown
    logger.info("🧠 DCBrain shutting down...")
    await close_db()
    await close_neo4j()
    await close_redis()
    logger.info("👋 Goodbye")


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


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add standard security headers to all HTTP responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# ── Routes ─────────────────────────────────────────────────────────────

app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(digital_twin.router, prefix="/api/digital-twin", tags=["Digital Twin"])
app.include_router(compliance.router, prefix="/api/compliance", tags=["Compliance"])
app.include_router(commissioning.router, prefix="/api/commissioning", tags=["Commissioning"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["Knowledge"])
app.include_router(graph.router, prefix="/api/graph", tags=["Graph"])
app.include_router(schedule_routes.router, prefix="/api/schedule", tags=["Schedule"])
app.include_router(supply_chain_routes.router, prefix="/api/supply-chain", tags=["Supply Chain"])
app.include_router(cascade.router)


# ── Global Exception Handler ──────────────────────────────────────────

from fastapi import Request
from fastapi.responses import JSONResponse


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions and return clean 500 error."""
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again."}
    )


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
