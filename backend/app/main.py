"""
Trust Analyst - Main FastAPI Application.
Autonomous Security Analyst on FalkorDB.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.config import settings
from backend.app.graph.client import get_graph_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("trust_analyst.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    logger.info("Initializing Trust Analyst Backend...")
    try:
        client = get_graph_client()
        if client.is_alive():
            logger.info(
                f"Connected to FalkorDB on {settings.FALKORDB_HOST}:{settings.FALKORDB_PORT} (graph: {settings.FALKORDB_GRAPH})"
            )
        else:
            logger.warning("FalkorDB is offline. Backend starting in degraded fail-closed mode.")
    except Exception as e:
        logger.error(f"FalkorDB startup warning: {e}")
    yield
    logger.info("Shutting down Trust Analyst Backend.")


app = FastAPI(
    title="Trust Analyst API",
    description="Autonomous Graph-Native Security Analyst powered by FalkorDB.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def get_health():
    """
    Health check endpoint.
    Reports FalkorDB connectivity. Investigations fail closed without an active database.
    """
    client = get_graph_client()
    db_alive = client.is_alive()
    status = "HEALTHY" if db_alive else "DEGRADED"
    status_code = 200 if db_alive else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": status,
            "falkordb_online": db_alive,
            "graph_name": settings.FALKORDB_GRAPH,
            "host": settings.FALKORDB_HOST,
            "port": settings.FALKORDB_PORT,
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)
