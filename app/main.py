"""FastAPI server for the Deal Intelligence Agent."""
from __future__ import annotations

import os
import logging
from typing import Literal
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict

from . import agent, llm
from .deals import SEED_CALLS, DealStore
from .memory import DocumentConflictError, bank_id_for, get_memory

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"

app = FastAPI(title="Deal Intelligence Agent", version="0.1.0")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])
app.mount("/static", StaticFiles(directory=STATIC), name="static")

store = DealStore()
memory = get_memory()


class LogCallRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    notes: str = Field(min_length=3, max_length=20000)
    outcome: str = Field(default="", max_length=2000)
    call_id: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]{1,80}$")
    supersedes_call_id: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]{1,80}$")


class FollowupRequest(BaseModel):
    tone: Literal["professional", "friendly", "concise"] = "professional"


@app.middleware("http")
async def protect_local_writes(request: Request, call_next):
    origin = request.headers.get("origin")
    if request.method not in {"GET", "HEAD", "OPTIONS"} and origin and origin != str(request.base_url).rstrip("/"):
        return JSONResponse(status_code=403, content={"detail": "Cross-origin writes are not allowed."})
    return await call_next(request)


@app.exception_handler(DocumentConflictError)
async def id_conflict(request: Request, exc: DocumentConflictError):
    return JSONResponse(
        status_code=409,
        content={"detail": f"{exc} If this was intentional, resubmit as a new call with supersedes_call_id={exc.document_id!r}."},
    )


@app.exception_handler(Exception)
async def backend_error(request: Request, exc: Exception):
    logging.getLogger(__name__).error("Request failed: %s", type(exc).__name__)
    return JSONResponse(status_code=503, content={"detail": "The operation could not finish. Check server logs and memory provider settings, then retry. Saved notes are preserved."})


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {
        "memory_backend": memory.name,
        "llm_configured": llm.is_configured(),
        "llm_model": llm.model_name(),
        "demo_only": memory.name == "local",
        "reset_available": memory.name == "local",
        "deals": [d.id for d in store.list()],
    }


@app.get("/api/deals")
def list_deals() -> dict:
    deals = []
    for deal in store.list():
        deals.append(
            {
                "id": deal.id,
                "company": deal.company,
                "contact": deal.contact,
                "value": deal.value,
                "stage": deal.stage,
                "competitors": deal.competitors,
                "memory_count": memory.count(bank_id_for(deal.id)),
            }
        )
    return {"deals": deals}


def _deal_or_404(deal_id: str):
    deal = store.get(deal_id)
    if deal is None:
        raise HTTPException(status_code=404, detail=f"Unknown deal: {deal_id}")
    return deal


@app.get("/api/deals/{deal_id}")
def deal_detail(deal_id: str) -> dict:
    deal = _deal_or_404(deal_id)
    data = agent.timeline(store, memory, deal_id)
    return {
        "id": deal.id,
        "company": deal.company,
        "contact": deal.contact,
        "contact_title": deal.contact_title,
        "value": deal.value,
        "stage": deal.stage,
        "competitors": deal.competitors,
        "timeline": data["memories"],
    }


@app.post("/api/deals/{deal_id}/brief")
def post_brief(deal_id: str, use_memory: bool = True) -> dict:
    _deal_or_404(deal_id)
    return agent.brief(store, memory, deal_id, use_memory=use_memory)


@app.post("/api/deals/{deal_id}/log-call")
def post_log_call(deal_id: str, req: LogCallRequest) -> dict:
    _deal_or_404(deal_id)
    try:
        return agent.log_call(store, memory, deal_id, req.notes, req.outcome, req.call_id, req.supersedes_call_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown deal: {deal_id}")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/api/deals/{deal_id}/followup")
def post_followup(deal_id: str, req: FollowupRequest) -> dict:
    _deal_or_404(deal_id)
    return agent.draft_followup(store, memory, deal_id, req.tone)


@app.get("/api/deals/{deal_id}/tactics")
def get_tactics(deal_id: str) -> dict:
    _deal_or_404(deal_id)
    return agent.suggest_tactics(store, memory, deal_id)


@app.get("/api/deals/{deal_id}/timeline")
def get_timeline(deal_id: str) -> dict:
    _deal_or_404(deal_id)
    return agent.timeline(store, memory, deal_id)


@app.post("/api/demo/seed")
def demo_seed() -> dict:
    """Load the staged call history so judges see a deal with memory on day one."""
    total = 0
    for deal_id, calls in SEED_CALLS.items():
        if store.get(deal_id) is None:
            continue
        for index, call in enumerate(calls):
            agent.log_call(store, memory, deal_id, call["notes"], call.get("outcome", ""), call_id=f"demo-v1-{deal_id}-{index}")
            total += 1
    return {"seeded_calls": total}


@app.post("/api/demo/reset")
def demo_reset() -> dict:
    """Wipe local memory + deals (local backend only) for a fresh demo run."""
    if memory.name != "local":
        raise HTTPException(status_code=400, detail="Reset only supported on the local memory backend.")
    memory.reset()  # type: ignore[attr-defined]
    agent.reset_call_receipts(memory)
    store.reset()
    return {"status": "reset"}


def main() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=int(os.environ.get("PORT", "8000")),
        reload=False,
    )


if __name__ == "__main__":
    main()
