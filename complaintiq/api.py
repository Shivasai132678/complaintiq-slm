"""Local pilot API: review, durable processing, exports and recovery."""

from __future__ import annotations

import csv
import io
import json
import logging
import os
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path
from threading import RLock
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from complaintiq.jobs import JobRunner
from complaintiq.models import DEFAULT_TRAINING
from complaintiq.service import ComplaintService
from complaintiq.storage import OUTSIDE, ComplaintStore, Conflict
from complaintiq.triage import DEPARTMENTS

ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger(__name__)
ComplaintText = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=6000)
]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, max_length=4000)]


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ComplaintInput(StrictInput):
    text: ComplaintText
    backend: Literal["baseline", "slm"] | None = None


class BatchInput(StrictInput):
    texts: Annotated[list[ComplaintText], Field(min_length=1, max_length=20)]
    backend: Literal["baseline", "slm"] | None = None


class JobInput(StrictInput):
    texts: Annotated[list[ComplaintText], Field(min_length=1, max_length=100)]
    request_key: Annotated[str, StringConstraints(min_length=8, max_length=100)]
    source: Literal["analysis", "import"] = "analysis"


class RevisionInput(StrictInput):
    revision: int = Field(ge=1)
    reason: Reason = ""


class ReviewInput(RevisionInput):
    product: str = Field(max_length=150)
    issue: str = Field(max_length=200)
    priority: str = Field(max_length=20)
    department: str = Field(max_length=100)


class TransitionInput(RevisionInput):
    status: Literal["Queued", "In review", "Resolved"]


def create_app(
    service: ComplaintService | None = None,
    static_dir: Path | None = None,
    evaluation_path: Path | None = None,
    db_path: Path | None = None,
) -> FastAPI:
    store = (
        service.store
        if service
        else ComplaintStore(
            str(
                db_path
                or Path(
                    os.environ.get("COMPLAINTIQ_DB_PATH", str(ROOT / "data/complaintiq.sqlite3"))
                )
            )
        )
    )
    guard = RLock()
    dist = (static_dir or ROOT / "frontend/dist").resolve()
    evaluation = evaluation_path or Path(
        os.environ.get("COMPLAINTIQ_EVALUATION_PATH", str(ROOT / "artifacts/evaluation.json"))
    )

    @lru_cache(maxsize=1)
    def get_service():
        with guard:
            if app.state.service is None:
                app.state.service = ComplaintService(
                    str(store.path),
                    backend=os.environ.get("COMPLAINTIQ_BACKEND", "baseline"),
                    model_path=os.environ.get("COMPLAINTIQ_MODEL_PATH"),
                    server_url=os.environ.get("COMPLAINTIQ_MODEL_URL"),
                )
            return app.state.service

    runner = JobRunner(store, lambda text, **kwargs: get_service().analyze(text, **kwargs))

    @asynccontextmanager
    async def lifespan(app):
        runner.start()
        try:
            yield
        finally:
            runner.stop()

    app = FastAPI(
        title="ComplaintIQ", version="2.0.0", docs_url=None, redoc_url=None, lifespan=lifespan
    )
    app.state.service, app.state.store, app.state.runner = service, store, runner
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]", "testserver"]
    )

    @app.middleware("http")
    async def local_writes(request: Request, call_next):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("origin")
            if origin and origin != f"{request.url.scheme}://{request.headers.get('host', '')}":
                return JSONResponse(
                    status_code=403,
                    content={"error": {"message": "Cross-origin writes are not allowed."}},
                )
            if request.headers.get("sec-fetch-site") == "cross-site":
                return JSONResponse(
                    status_code=403,
                    content={"error": {"message": "Cross-site writes are not allowed."}},
                )
            if request.headers.get("content-type", "").split(";")[0] != "application/json":
                return JSONResponse(
                    status_code=415, content={"error": {"message": "Use application/json."}}
                )
            # Bound bytes even for chunked requests, before JSON parsing.
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 2 * 1024 * 1024:
                    return JSONResponse(
                        status_code=413, content={"error": {"message": "Request exceeds 2 MB."}}
                    )
            request._body = bytes(body)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "message": "Check required fields, input lengths, dates and allowed values. Complaints allow 1–6000 characters; imports allow 1–100 rows."
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        return JSONResponse(
            status_code=exc.status_code,
            headers=exc.headers,
            content={"error": {"message": str(exc.detail)}},
        )

    @app.exception_handler(Conflict)
    async def conflict(request, exc):
        return JSONResponse(status_code=409, content={"error": {"message": str(exc)}})

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return JSONResponse(status_code=404, content={"error": {"message": "Record not found."}})

    @app.exception_handler(ValueError)
    async def bad_value(request, exc):
        return JSONResponse(status_code=422, content={"error": {"message": str(exc)}})

    def taxonomy():
        if service:
            return service.baseline.taxonomy
        result: dict[str, list[str]] = {}
        with DEFAULT_TRAINING.open() as f:
            for r in csv.DictReader(f):
                if r["issue"] not in result.setdefault(r["product"], []):
                    result[r["product"]].append(r["issue"])
        return result

    @app.get("/api/config")
    def config():
        return {
            "taxonomy": taxonomy(),
            "departments": [*DEPARTMENTS.values(), "Manual Review Team"],
            "routing": DEPARTMENTS,
            "outside": OUTSIDE,
            "input_limit": 6000,
            "model_excerpt_limit": 2000,
        }

    @app.get("/api/health")
    def health():
        try:
            current = get_service()
            check = getattr(current.model, "check_health", None)
            if check:
                check()
        except Exception as exc:
            LOGGER.warning("model_health_failed error_type=%s", type(exc).__name__)
            raise HTTPException(
                503, "The classification engine is unavailable. Check the local model server."
            ) from None
        data_dir = DEFAULT_TRAINING.parent / ("finetuning" if current.backend == "slm" else "")
        sizes = {}
        for name in ("training.csv", "validation.csv", "test.csv"):
            with (data_dir / name).open() as f:
                sizes[name] = sum(1 for _ in csv.DictReader(f))
        return {
            "status": "ok",
            "backend": current.backend,
            "model_version": current.model.model_version,
            "training_status": "trained_exported" if current.backend == "slm" else "deferred",
            "slm_status": "ready" if current.backend == "slm" else "not_configured",
            "dataset_size": sum(sizes.values()),
            "training_size": sizes["training.csv"],
            "test_size": sizes["test.csv"],
            "products": sorted(taxonomy()),
            "taxonomy": taxonomy(),
        }

    @app.get("/api/complaints")
    def legacy_list(limit: Annotated[int, Query(ge=1, le=1000)] = 500):
        return {"items": store.list()[:limit]}

    def filters(
        q="",
        status="",
        product="",
        priority="",
        department="",
        start="",
        end="",
        confirmed="",
        sort="newest",
        page=1,
        page_size=25,
        urgent="",
    ):
        from datetime import date

        for value in (start, end):
            if value:
                date.fromisoformat(value)
        if start and end and start > end:
            raise ValueError("Start date must precede end date.")
        return dict(
            q=q,
            status=status,
            product=product,
            priority=priority,
            department=department,
            start=start,
            end=end,
            confirmed=confirmed,
            sort=sort,
            page=page,
            page_size=page_size,
            urgent=urgent,
        )

    @app.get("/api/cases")
    def cases(
        q: str = "",
        status: str = "",
        product: str = "",
        priority: str = "",
        department: str = "",
        start: str = "",
        end: str = "",
        confirmed: str = "",
        sort: Literal["newest", "oldest", "priority"] = "newest",
        page: int = Query(1, ge=1),
        page_size: int = Query(25, ge=1, le=100),
        urgent: str = "",
    ):
        return store.search(
            **filters(
                q,
                status,
                product,
                priority,
                department,
                start,
                end,
                confirmed,
                sort,
                page,
                page_size,
                urgent,
            )
        )

    @app.get("/api/cases/export")
    def export(
        kind: Literal["cases", "reviewed"] = "cases",
        q: str = "",
        status: str = "",
        product: str = "",
        priority: str = "",
        department: str = "",
        start: str = "",
        end: str = "",
        confirmed: str = "",
        sort: str = "newest",
        urgent: str = "",
    ):
        args = filters(
            q, status, product, priority, department, start, end, confirmed, sort, urgent=urgent
        )
        if kind == "reviewed":
            args["confirmed"] = "1"
        args["page_size"] = 1000000
        rows = store.search(**args)["items"]
        if kind == "reviewed":
            rows = [r for r in rows if r["issue"] in taxonomy().get(r["product"], [])]
        fields = (
            [
                "id",
                "text",
                "product",
                "issue",
                "priority",
                "department",
                "status",
                "confirmed",
                "model_version",
                "created_at",
            ]
            if kind == "cases"
            else ["id", "text", "product", "issue"]
        )
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            clean = {k: r.get(k, "") for k in fields}
            for k, v in clean.items():
                if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
                    clean[k] = "'" + v
            writer.writerow(clean)
        return Response(
            out.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="complaintiq-{kind}.csv"'},
        )

    @app.get("/api/cases/{case_id}")
    def case(case_id: str):
        return store.get(case_id)

    @app.patch("/api/cases/{case_id}/review")
    def review(case_id: str, payload: ReviewInput):
        return store.change(case_id, payload.revision, "review", payload.model_dump(), taxonomy())

    @app.post("/api/cases/{case_id}/notes")
    def note(case_id: str, payload: RevisionInput):
        return store.change(case_id, payload.revision, "note", payload.model_dump(), taxonomy())

    @app.post("/api/cases/{case_id}/transition")
    def transition(case_id: str, payload: TransitionInput):
        return store.change(
            case_id, payload.revision, "transition", payload.model_dump(), taxonomy()
        )

    @app.get("/api/overview")
    def overview():
        return store.overview()

    @app.get("/api/analytics")
    def legacy_analytics():
        from collections import Counter

        rows = store.list()
        return {
            "total": len(rows),
            "by_product": dict(Counter(r.get("product") for r in rows)),
            "by_priority": dict(Counter(r.get("priority") for r in rows)),
            "by_department": dict(Counter(r.get("department") for r in rows)),
            "by_backend": dict(Counter(r.get("backend") for r in rows)),
            "needs_review": sum(r.get("status") == "Needs review" for r in rows),
            "average_latency_ms": round(sum(r.get("latency_ms", 0) for r in rows) / len(rows), 2)
            if rows
            else 0,
        }

    @app.post("/api/jobs", status_code=202)
    def submit(payload: JobInput):
        runner.start()
        return store.submit_job(payload.texts, payload.request_key, payload.source)

    @app.get("/api/jobs")
    def jobs():
        return {"items": store.jobs()}

    @app.get("/api/jobs/{job_id}")
    def job(job_id: str):
        return store.job(job_id)

    @app.post("/api/jobs/{job_id}/{action}")
    def control(job_id: str, action: Literal["cancel", "retry"]):
        runner.start()
        return store.control_job(job_id, action)

    def sync_job(texts, backend):
        configured = (
            service.backend if service else os.environ.get("COMPLAINTIQ_BACKEND", "baseline")
        )
        if backend and backend != configured:
            raise HTTPException(422, "Requested engine is not the configured engine.")
        runner.start()
        result = store.submit_job(texts, str(uuid4()), "analysis")
        try:
            return runner.wait(result["id"])
        except TimeoutError as exc:
            raise HTTPException(504, str(exc)) from None

    @app.post("/api/complaints", status_code=201)
    def create(payload: ComplaintInput):
        result = sync_job([payload.text], payload.backend)["rows"][0]
        if result["state"] != "complete":
            raise HTTPException(503, result["error"])
        return store.get(result["case_id"])

    @app.post("/api/batch")
    def batch(payload: BatchInput):
        job = sync_job(payload.texts, payload.backend)
        return {
            "items": [
                store.get(r["case_id"])
                if r["state"] == "complete"
                else {"text": r["text"], "error": r["error"]}
                for r in job["rows"]
            ],
            "saved": job["counts"]["complete"],
        }

    @app.get("/api/system")
    def system():
        folder = store.path.parent / "backups"
        backups = sorted(
            folder.glob(f"{store.path.stem}-*.sqlite3"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        with store._connect() as c:
            counts = dict(
                c.execute("SELECT state,count(*) FROM job_rows GROUP BY state").fetchall()
            )
        return {
            "database_bytes": store.path.stat().st_size,
            "schema_version": 1,
            "backups": [{"name": p.name, "bytes": p.stat().st_size} for p in backups[:20]],
            "pending_rows": counts.get("pending", 0),
            "running_rows": counts.get("running", 0),
            "failed_rows": counts.get("failed", 0),
            "mode": "Local operator · localhost only",
        }

    @app.post("/api/backups")
    def backup():
        path = store.backup()
        return {"name": path.name, "bytes": path.stat().st_size}

    @app.get("/api/evaluation")
    def measured_evaluation():
        try:
            value = json.loads(evaluation.read_text())
            if not isinstance(value, dict) or value.get("status") not in ("measured", "complete"):
                raise ValueError()
            return value
        except (OSError, ValueError):
            raise HTTPException(503, "Measured evaluation is unavailable.") from None

    @app.get("/{path:path}")
    def frontend(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "API route not found.")
        target = (dist / path).resolve()
        if not target.is_relative_to(dist):
            raise HTTPException(404, "File not found.")
        if target.is_file():
            return FileResponse(target)
        if Path(path).suffix or path.startswith("assets/"):
            raise HTTPException(404, "File not found.")
        if not (dist / "index.html").is_file():
            raise HTTPException(503, "Frontend build unavailable. Run npm run build in frontend.")
        return FileResponse(dist / "index.html")

    return app


app = create_app()
