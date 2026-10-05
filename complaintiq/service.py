"""Application service: classify, explain, triage and persist each complaint."""

from __future__ import annotations

import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from complaintiq.models import DEFAULT_TRAINING, BaselineClassifier, LocalSLMClassifier
from complaintiq.scope import ScopeGate, default_gate
from complaintiq.server_model import ServerSLMClassifier
from complaintiq.storage import ComplaintStore
from complaintiq.triage import routing, triage


class ComplaintService:
    """Default is a real trained baseline; opt into a provided local GGUF SLM.

    SLM errors propagate to the UI for an explicit error state. No silent backend
    switching. Raw text remains in the user's local SQLite file.
    """

    def __init__(
        self,
        db_path: str = "data/complaintiq.sqlite3",
        backend: str = "baseline",
        model_path: str | None = None,
        training_path: Path | str = DEFAULT_TRAINING,
        slm_lime: bool = False,
        server_url: str | None = None,
        scope_gate: bool | ScopeGate = True,
    ) -> None:
        if backend not in {"baseline", "slm"}:
            raise ValueError("Supported backend values are baseline and slm.")
        if backend == "slm" and not model_path:
            raise ValueError("Select a local GGUF model path to enable SLM inference.")
        self.baseline = BaselineClassifier(training_path)
        self.model: BaselineClassifier | LocalSLMClassifier
        if backend == "baseline":
            self.model = self.baseline
        elif server_url:
            self.model = ServerSLMClassifier(str(model_path), self.baseline.taxonomy, server_url)
        else:
            self.model = LocalSLMClassifier(str(model_path), self.baseline.taxonomy)
        self.backend = backend
        self.slm_lime = slm_lime
        self.store = ComplaintStore(db_path)
        # Out-of-scope text is routed to review before the classifier runs.
        self.scope: ScopeGate | None = (
            scope_gate
            if isinstance(scope_gate, ScopeGate)
            else default_gate()
            if scope_gate
            else None
        )

    def analyze(
        self, text: str, *, persist: bool = True, record_id: str | None = None
    ) -> dict[str, Any]:
        """Reject invalid input before inference or storage, then return a record."""
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Enter a non-empty complaint.")
        text = text.strip()
        if len(text) > 6000:
            raise ValueError("Complaint must be at most 6000 characters.")
        started = time.perf_counter()
        scope = self.scope.check(text) if self.scope else None
        if scope and not scope["in_scope"]:
            prediction: dict[str, Any] = {
                "product": "Unknown",
                "issue": "Needs review",
                "tokens_input": 0,
                "tokens_output": 0,
            }
        else:
            prediction = self.model.classify(text)
        explanation: list[dict[str, Any]]
        if scope and not scope["in_scope"]:
            explanation = []
            method = "Not classified: outside the supported scope"
        elif self.backend == "slm" and not self.slm_lime:
            explanation = []
            method = "SLM LIME disabled; enable slm_lime for a slow 24-perturbation explanation"
        else:
            method = (
                "LIME product attribution"
                if self.backend == "baseline"
                else "LIME SLM attribution (24 perturbations; exploratory)"
            )
            try:
                explanation = self.model.explain(text, prediction["product"])
            except Exception as exc:
                # Attribution is optional; preserve the validated prediction.
                explanation = []
                method = f"LIME unavailable ({type(exc).__name__}); prediction preserved"
        priority = triage(text)
        record: dict[str, Any] = {
            "id": record_id or "CQ-" + uuid4().hex[:10].upper(),
            "text": text,
            **prediction,
            **priority,
            **routing(prediction["product"], priority["priority"]),
            "summary": self._summary(text),
            "summary_method": "Extractive preview",
            "status": "Needs review"
            if prediction["product"] == "Unknown" or priority["priority"] == "Critical"
            else "Queued",
            "backend": self.backend,
            "model_version": self.model.model_version,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "explanation": explanation,
            "explanation_method": method,
            "scope_check": scope,
        }
        if persist:
            self.store.save(record)
        return record

    @staticmethod
    def _summary(text: str) -> str:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        preview = " ".join(sentences[:2])
        return preview if len(preview) <= 320 else preview[:317] + "..."

    def list_complaints(self) -> list[dict[str, Any]]:
        return self.store.list()

    def analytics(self) -> dict[str, Any]:
        rows = self.list_complaints()
        return {
            "total": len(rows),
            "by_product": dict(Counter(row["product"] for row in rows)),
            "by_priority": dict(Counter(row["priority"] for row in rows)),
            "by_department": dict(Counter(row["department"] for row in rows)),
            "by_backend": dict(Counter(row["backend"] for row in rows)),
            "needs_review": sum(row["status"] == "Needs review" for row in rows),
            "average_latency_ms": round(sum(row["latency_ms"] for row in rows) / len(rows), 2)
            if rows
            else 0.0,
        }
