"""Orrery API."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import Base, engine
from routers import auth, graph, ingest, quiz, review, tutor
from services.llm.registry import get_client

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="Orrery API",
    version="0.1.0",
    description="Merged study platform: knowledge graph, adaptive mastery, Bedrock tutoring.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(graph.router)
app.include_router(ingest.router)
app.include_router(quiz.router)
app.include_router(review.router)
app.include_router(tutor.router)


@app.on_event("startup")
async def startup():
    # Alembic owns the schema in deployment; this keeps a fresh clone runnable.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    client = await get_client()
    logging.getLogger("orrery").info(
        "database=%s llm=%s",
        "postgres" if settings.is_postgres else "sqlite",
        client.provider_name,
    )


@app.get("/api/health")
async def health():
    client = await get_client()
    return {
        "status": "ok",
        "database": "postgres" if settings.is_postgres else "sqlite",
        "llm": client.provider_name,
    }
