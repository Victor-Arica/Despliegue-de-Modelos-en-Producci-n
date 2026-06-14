"""FastAPI service exposing the RAG engine."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.rag import engine

app = FastAPI(
    title="MLOps RAG API",
    description="Minimal Retrieval-Augmented Generation API over local .txt docs.",
    version="1.0.0",
)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Question about the docs.")


class AskResponse(BaseModel):
    answer: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "index_ready": engine.ready, "chunks": engine.num_chunks}


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    try:
        answer = engine.ask(request.question)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Upstream error: {exc}") from exc
    return AskResponse(answer=answer)
