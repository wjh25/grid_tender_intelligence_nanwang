from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db import close_pool, open_pool
from app.repositories import (
    get_document_blocks,
    get_southern_grid_tender,
    get_tender_packages,
    get_tender_requirements,
    list_southern_grid_tenders,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    open_pool()
    yield
    close_pool()


app = FastAPI(title="Grid Tender Intelligence API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/southern-grid/tenders")
def southern_grid_tenders(
    q: str | None = Query(default=None, description="标题、项目编号、采购人等关键词"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    return list_southern_grid_tenders(q=q, limit=limit, offset=offset)


@app.get("/api/southern-grid/tenders/{document_id}")
def southern_grid_tender(document_id: int) -> dict[str, Any]:
    tender = get_southern_grid_tender(document_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender document not found")
    return {
        "document": tender,
        "blocks": get_document_blocks(document_id),
        "requirements": get_tender_requirements(document_id),
        "packages": get_tender_packages(document_id),
    }


@app.get("/api/southern-grid/tenders/{document_id}/blocks")
def southern_grid_tender_blocks(document_id: int) -> list[dict[str, Any]]:
    return get_document_blocks(document_id)


@app.get("/api/southern-grid/tenders/{document_id}/requirements")
def southern_grid_tender_requirements(document_id: int) -> list[dict[str, Any]]:
    return get_tender_requirements(document_id)


FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    async def spa_fallback(path: str):
        index_path = FRONTEND_DIST / "index.html"
        if index_path.is_file():
            from fastapi.responses import FileResponse
            return FileResponse(index_path)
        return {"detail": "Frontend not found"}
