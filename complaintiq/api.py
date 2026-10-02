"""Same-origin REST service and React SPA host for the local assignment demo.

Run with ``uvicorn complaintiq.api:app --host 127.0.0.1 --port 8501``.
SLM weights and fine-tuning are intentionally deferred; API accepts baseline only.
"""

from __future__ import annotations

import csv
import json
import logging
from functools import lru_cache
from pathlib import Path
from threading import RLock
from typing import Annotated, Any, Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from starlette.exceptions import HTTPException as StarletteHTTPException

from complaintiq.models import DEFAULT_TRAINING
from complaintiq.service import ComplaintService

ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger(__name__)
ComplaintText = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=6000)
]


class ComplaintInput(BaseModel):
    """Only the active backend is exposed, never server filesystem model paths."""

    model_config = ConfigDict(extra="forbid")
    text: ComplaintText
    backend: Literal["baseline"] = "baseline"


class BatchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    texts: Annotated[list[ComplaintText], Field(min_length=1, max_length=20)]
    backend: Literal["baseline"] = "baseline"


def create_app(
    service: ComplaintService | None = None,
    static_dir: Path | None = None,
    evaluation_path: Path | None = None,
) -> FastAPI:
    """Construct isolated instances for tests; default retains existing demo DB."""
    app = FastAPI(title="ComplaintIQ", version="1.0.0", docs_url=None, redoc_url=None)
    app.state.service = service
    dist = (static_dir or ROOT / "frontend" / "dist").resolve()
    evaluation = evaluation_path or ROOT / "artifacts" / "evaluation.json"
    service_lock = RLock()

    @lru_cache(maxsize=1)
    def get_service() -> ComplaintService:
        with service_lock:
            if app.state.service is None:
                app.state.service = ComplaintService(str(ROOT / "data" / "complaintiq.sqlite3"))
            return app.state.service

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "invalid_input",
                    "message": "Provide non-empty complaint text up to 6000 characters; batches contain 1–20 complaints. Only baseline is available.",
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            headers=exc.headers,
            content={"error": {"code": "request_failed", "message": str(exc.detail)}},
        )

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        current = get_service()
        sizes: dict[str, int] = {}
        for filename in ("training.csv", "validation.csv", "test.csv"):
            path = DEFAULT_TRAINING.parent / filename
            if path.is_file():
                with path.open(encoding="utf-8") as handle:
                    sizes[filename] = sum(1 for _ in csv.DictReader(handle))
        return {
            "status": "ok",
            "backend": "baseline",
            "model_version": current.model.model_version,
            "training_status": "deferred",
            "slm_status": "not_configured",
            "dataset_size": sum(sizes.values()),
            "training_size": sizes.get("training.csv", 0),
            "test_size": sizes.get("test.csv", 0),
            "products": sorted(current.baseline.taxonomy),
            "taxonomy": current.baseline.taxonomy,
        }

    @app.get("/api/complaints")
    def complaints(limit: Annotated[int, Query(ge=1, le=1000)] = 500) -> dict[str, Any]:
        return {"items": get_service().list_complaints()[:limit]}

    def analyze_one(text: str) -> dict[str, Any]:
        try:
            return get_service().analyze(text)
        except ValueError as exc:
            raise HTTPException(422, "Complaint could not be analyzed; check the text.") from exc
        except Exception as exc:
            LOGGER.exception("Complaint analysis failed")
            raise HTTPException(503, "Analysis is temporarily unavailable. Please retry.") from exc

    @app.post("/api/complaints", status_code=201)
    def create_complaint(payload: ComplaintInput) -> dict[str, Any]:
        return analyze_one(payload.text)

    @app.post("/api/batch")
    def batch(payload: BatchInput) -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        saved = 0
        for text in payload.texts:
            try:
                items.append(analyze_one(text))
                saved += 1
            except HTTPException as exc:
                items.append({"text": text, "error": str(exc.detail)})
        return {"items": items, "saved": saved}

    @app.get("/api/analytics")
    def analytics() -> dict[str, Any]:
        return get_service().analytics()

    @app.get("/api/evaluation")
    def measured_evaluation() -> dict[str, Any]:
        try:
            value = json.loads(evaluation.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("Evaluation is not an object")
            return value
        except (OSError, ValueError) as exc:
            raise HTTPException(503, "Measured evaluation is unavailable.") from exc

    @app.get("/{path:path}")
    def frontend(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "API route not found.")
        target = (dist / path).resolve()
        if not target.is_relative_to(dist):
            raise HTTPException(404, "File not found.")
        if target.is_file():
            return FileResponse(target)
        # Missing asset filenames never receive HTML; application routes do.
        if Path(path).suffix or path.startswith("assets/"):
            raise HTTPException(404, "File not found.")
        index = dist / "index.html"
        if not index.is_file():
            raise HTTPException(503, "Frontend build unavailable. Run npm run build in frontend.")
        return FileResponse(index)

    return app


app = create_app()
