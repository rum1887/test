"""
Runtime Trust Layer - Main FastAPI Application.
Graph-Native Runtime Security Platform for AI Agents and Kubernetes.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from graph.client import get_graph_client
from graph.schema.schema import initialize_schema
from graph.fixtures.seeder import seed_scenarios

from apps.api.routes.health import router as health_router
from apps.api.routes.graph_routes import router as graph_router
from apps.api.routes.workloads import router as workloads_router
from apps.api.routes.agents import router as agents_router
from apps.api.routes.events import router as events_router
from apps.api.routes.security import router as security_router
from apps.api.routes.containment import router as containment_router
from apps.api.routes.scenarios import router as scenarios_router
from apps.api.routes.audit import router as audit_router
from apps.api.routes.compliance import router as compliance_router
from apps.api.routes.target_app import router as target_app_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("trustlayer.api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle startup and shutdown handler."""
    logger.info("Initializing Runtime Trust Layer Backend...")
    try:
        client = get_graph_client()
        if client.is_alive():
            # Check if graph already has nodes; if not, seed canonical state
            res = client.query("MATCH (n) RETURN count(n) AS cnt")
            node_count = res[0][0] if res else 0
            if node_count == 0:
                logger.info("Graph is empty. Seeding initial baseline fixtures...")
                seed_scenarios(client)
            else:
                logger.info(f"FalkorDB connected with {node_count} existing nodes.")
        else:
            logger.warning("FalkorDB is unreachable at startup. System starting in degraded mode.")
    except Exception as e:
        logger.error(f"Startup initialization warning: {e}")
    yield
    logger.info("Shutting down Runtime Trust Layer Backend.")

app = FastAPI(
    title="Runtime Trust Layer API",
    description="Graph-native security control plane connecting Workload Trust, AI Agent Trust, and Runtime Enforcement.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration allowing local frontend development and hosted deployments
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins in dev & demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(health_router)
app.include_router(graph_router)
app.include_router(workloads_router)
app.include_router(agents_router)
app.include_router(events_router)
app.include_router(security_router)
app.include_router(containment_router)
app.include_router(scenarios_router)
app.include_router(audit_router)
app.include_router(compliance_router)
app.include_router(target_app_router)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc),
            "path": request.url.path,
        },
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.api.main:app", host="0.0.0.0", port=8000, reload=True)
