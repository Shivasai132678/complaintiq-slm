"""ComplaintIQ: local complaint analysis, saved routing, and measured model evidence.

Adapts the workstation concept of MohammedHssan11/complaint-routing-intelligence.
See THIRD_PARTY_NOTICES.md for upstream attribution and licensing.
Run with: streamlit run app.py
"""

from __future__ import annotations

import json
import os
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from complaintiq.service import ComplaintService

ROOT = Path(__file__).resolve().parent
EXAMPLES = {
    "Credit report dispute": "My credit report contains a credit card account that is not mine. I disputed the incorrect account twice, but it still appears on my report and is hurting my credit score.",
    "Credit card charge": "I found an unauthorized charge on my credit card statement. I notified the card company immediately, but they refused to investigate and charged interest on the disputed amount.",
    "Bank account fee": "My bank charged an overdraft fee even though I had enough money in my checking account. Customer service promised to reverse it, but the fee remains on my statement.",
}


@st.cache_resource(show_spinner=False)
def get_service(
    db_path: str, backend: str, model_path: str | None, slm_lime: bool = False
) -> ComplaintService:
    """Share model resources across reruns; the database service owns its connections."""
    return ComplaintService(
        db_path=db_path, backend=backend, model_path=model_path, slm_lime=slm_lime
    )


def card(label: str, value: object) -> None:
    """Render escaped result fields without allowing complaint text to inject markup."""
    st.markdown(
        f'<div class="result-card"><div class="result-label">{escape(label)}</div>'
        f'<div class="result-value">{escape(str(value))}</div></div>',
        unsafe_allow_html=True,
    )


def model_settings() -> tuple[str, str | None]:
    mode = st.sidebar.selectbox(
        "Analysis engine",
        ["Baseline (TF-IDF + Logistic Regression)", "Local SLM (GGUF)"],
        key="model_mode",
    )
    backend = "slm" if mode.startswith("Local") else "baseline"
    path = None
    if backend == "slm":
        path = (
            st.sidebar.text_input(
                "GGUF file path", placeholder="/path/to/model.Q4_K_M.gguf", key="model_path"
            ).strip()
            or None
        )
        st.sidebar.caption(
            "Optional · Not configured. Model training is deferred; select an existing GGUF file to enable inference."
        )
        st.sidebar.checkbox(
            "SLM token explanation (slow)",
            key="slm_lime",
            help="LIME runs 24 additional model perturbations. Enable for a detailed explanation when presentation time allows.",
        )
    else:
        st.sidebar.caption(
            "Traditional ML baseline. Use Model evidence to inspect its training and evaluation."
        )
    st.sidebar.divider()
    st.sidebar.caption(
        "Priority and routing follow documented rules. All outputs remain reviewable."
    )
    return backend, path


def ensure_model(backend: str, model_path: str | None) -> bool:
    if backend == "slm" and (not model_path or not Path(model_path).is_file()):
        st.error("Choose an existing GGUF file in the sidebar before using Local SLM.")
        return False
    return True


def show_result(result: dict[str, Any]) -> None:
    st.subheader("Analysis result")
    st.caption(
        f"Complaint #{result.get('id', '—')} · {result.get('backend', '—')} · {result.get('model_version', '—')}"
    )
    left, middle, right = st.columns(3)
    with left:
        card("Product", result.get("product", "Needs review"))
    with middle:
        card("Priority · rule based", result.get("priority", "Needs review"))
    with right:
        card("Route to", result.get("department", "Manual review"))
    card("Issue", result.get("issue", "Needs review"))
    st.write("**Why this priority**")
    st.write(result.get("priority_reason", "No priority explanation available."))
    st.write("**Suggested next step**")
    st.write(result.get("action", "Review the complaint manually."))
    if result.get("summary"):
        st.write(f"**{result.get('summary_method', 'Complaint excerpt')}**")
        st.write(result["summary"])
    timing = f"Status: {result.get('status', 'Needs review')} · Processing: {float(result.get('latency_ms', 0)) / 1000:.2f}s"
    if result.get("backend") == "slm":
        timing += f" · Input tokens: {result.get('tokens_input', 0)} · Output tokens: {result.get('tokens_output', 0)}"
        if result.get("cached"):
            timing += " · Cached inference"
    st.caption(timing)
    with st.expander("Prediction explanation and saved record"):
        attribution = result.get("explanation", [])
        if attribution:
            st.caption(result.get("explanation_method", "Token attribution"))
            st.dataframe(pd.DataFrame(attribution), hide_index=True, width="stretch")
            st.caption(
                "Positive weights support the predicted product; these are explanations, not confidence percentages."
            )
        else:
            st.info(
                result.get(
                    "explanation_method", "No token attribution was returned for this prediction."
                )
            )
        st.json(result)


def analyze_view(db_path: str, backend: str, model_path: str | None) -> None:
    st.subheader("Turn a complaint into a clear next step")
    st.write("Classify the complaint, explain its urgency, and route it to the right team.")
    with st.expander("Try an example"):
        example = st.selectbox("Example complaint", list(EXAMPLES), key="example_choice")
        if st.button("Use this example", key="use_example"):
            st.session_state["complaint_text"] = EXAMPLES[example]
        st.caption(
            "These are illustrative inputs. They are analyzed and saved only when you submit."
        )
    with st.form("analysis_form"):
        text = st.text_area(
            "Complaint narrative",
            height=180,
            max_chars=6000,
            placeholder="Describe what happened, which financial product was involved, and what remains unresolved…",
            key="complaint_text",
        )
        submitted = st.form_submit_button("Analyze complaint", type="primary", key="analyze_submit")
    if submitted and ensure_model(backend, model_path):
        if not text.strip():
            st.error("Enter a complaint narrative before analyzing.")
        else:
            try:
                with st.spinner("Analyzing and saving the complaint…"):
                    st.session_state["last_result"] = get_service(
                        db_path,
                        backend,
                        model_path,
                        backend == "slm" and st.session_state.get("slm_lime", False),
                    ).analyze(text)
            except Exception as error:
                st.error(f"Analysis could not finish: {error}")
    if "last_result" in st.session_state:
        show_result(st.session_state["last_result"])


def saved_rows(db_path: str) -> list[dict[str, Any]]:
    return get_service(db_path, "baseline", None).list_complaints()


def csv_export(frame: pd.DataFrame) -> str:
    """Neutralize spreadsheet formulas in text fields before CSV export."""
    output = frame.copy()
    for column in output.select_dtypes(include=["object", "string"]).columns:
        output[column] = output[column].map(
            lambda value: (
                "'" + value
                if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@"))
                else value
            )
        )
    return output.to_csv(index=False)


def queue_view(db_path: str) -> None:
    st.subheader("Complaint queue")
    rows = saved_rows(db_path)
    if not rows:
        st.info("Your queue is empty. Analyze a complaint to start building a saved history.")
        return
    frame = pd.DataFrame(rows)
    left, right = st.columns([2, 1])
    query = left.text_input(
        "Search complaints", placeholder="Search narratives, products, or issues"
    )
    priorities = right.multiselect("Priority", sorted(frame["priority"].dropna().unique()))
    if query:
        frame = frame[
            frame[[c for c in ["text", "product", "issue"] if c in frame]]
            .astype(str)
            .apply(lambda row: row.str.contains(query, case=False, regex=False).any(), axis=1)
        ]
    if priorities:
        frame = frame[frame["priority"].isin(priorities)]
    st.caption(f"{len(frame)} of {len(rows)} saved complaints")
    columns = [
        c
        for c in [
            "id",
            "created_at",
            "product",
            "issue",
            "priority",
            "department",
            "status",
            "backend",
            "text",
        ]
        if c in frame
    ]
    st.dataframe(frame[columns], hide_index=True, width="stretch")
    st.download_button(
        "Export filtered queue", csv_export(frame[columns]), "complaintiq_queue.csv", "text/csv"
    )
    if not frame.empty:
        selected = st.selectbox("Inspect complaint", frame["id"].tolist())
        with st.expander("Full analysis", expanded=False):
            show_result(next(row for row in rows if row["id"] == selected))


def analytics_view(db_path: str) -> None:
    st.subheader("Operational overview")
    rows = saved_rows(db_path)
    if not rows:
        st.info("Analytics will appear after complaints are analyzed and saved.")
        return
    frame = pd.DataFrame(rows)
    a, b = st.columns(2)
    a.metric("Complaints analyzed", len(frame))
    b.metric("High / critical priority", int(frame["priority"].isin(["High", "Critical"]).sum()))
    c, d = st.columns(2)
    c.metric("Products represented", frame["product"].nunique())
    d.metric("Mean processing time", f"{pd.to_numeric(frame['latency_ms']).mean() / 1000:.2f}s")
    st.caption(
        "Counts reflect saved predictions. Priority is assigned by rules, and processing times may mix engines."
    )
    left, right = st.columns(2)
    with left:
        st.write("**Product distribution**")
        st.bar_chart(frame["product"].value_counts(), color="#2864dc")
    with right:
        st.write("**Priority distribution**")
        st.bar_chart(frame["priority"].value_counts(), color="#27a494")
    st.write("**Routing workload**")
    st.bar_chart(frame["department"].value_counts(), color="#6d75cf")


def evidence_view() -> None:
    st.subheader("Model evidence")
    st.write(
        "Compare measured classification results before drawing conclusions about model quality."
    )
    report = ROOT / "artifacts" / "evaluation.json"
    if not report.exists():
        st.info("No evaluation report yet. Run the evaluation script to populate this view.")
    else:
        try:
            payload = json.loads(report.read_text(encoding="utf-8"))
            st.caption(
                f"{payload.get('model', 'Model')} · {payload.get('backend', '—')} · {payload.get('test_size', '—')} held-out complaints"
            )
            product = payload.get("product", {})
            if product and payload.get("status") == "measured":
                a, b = st.columns(2)
                a.metric("Product accuracy", f"{product.get('accuracy', 0):.1%}")
                b.metric("Product macro F1", f"{product.get('f1_macro', 0):.3f}")
                c, d = st.columns(2)
                c.metric("Issue macro F1", f"{payload.get('issue', {}).get('f1_macro', 0):.3f}")
                d.metric("Product + issue accuracy", f"{payload.get('joint_accuracy', 0):.1%}")
                labels = product.get("labels", [])
                matrix = product.get("confusion_matrix", [])
                if labels and matrix:
                    st.write("**Product confusion matrix**")
                    st.caption("Rows: actual product. Columns: predicted product.")
                    st.dataframe(
                        pd.DataFrame(matrix, index=labels, columns=labels), width="stretch"
                    )
                st.caption(
                    "Measured on the supplied held-out dataset. These results apply to this experiment, not all financial complaints."
                )
            limitations = payload.get("limitations", [])
            if isinstance(limitations, str):
                limitations = [limitations]
            for limitation in limitations:
                st.caption(str(limitation))
            with st.expander("Full evaluation details"):
                st.json(payload)
            st.download_button(
                "Download evaluation report",
                report.read_bytes(),
                "evaluation.json",
                "application/json",
            )
        except (OSError, ValueError) as error:
            st.error(f"Could not read evaluation report: {error}")
    st.write("**Model comparison readiness**")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Engine": "TF-IDF + Logistic Regression",
                    "Status": "Baseline available",
                    "Evaluation": "Measured report above" if report.exists() else "Report pending",
                },
                {
                    "Engine": "Local SLM",
                    "Status": "Model / training deferred",
                    "Evaluation": "Not evaluated",
                },
                {
                    "Engine": "Fine-tuned SLM",
                    "Status": "Training deferred",
                    "Evaluation": "Not evaluated",
                },
            ]
        ),
        hide_index=True,
        width="stretch",
    )
    st.write("**How this demo makes decisions**")
    st.markdown(
        "- **Baseline:** TF-IDF features and Logistic Regression.\n- **Local SLM:** a GGUF instruction model with constrained complaint categories.\n- **Priority:** documented text rules with an explanation.\n- **Routing and actions:** mappings and reviewed templates.\n- **Human review:** required when an output is unsupported or uncertain."
    )
    st.caption(
        "A local prompted SLM is not a fine-tuned model. A cloud training adapter must be trained, exported, and evaluated before describing it as fine-tuned."
    )


def batch_view(db_path: str, backend: str, model_path: str | None) -> None:
    st.subheader("Batch analysis")
    st.write(
        "Upload a CSV with a `text` column. Up to 20 complaints can be analyzed and saved per batch."
    )
    uploaded = st.file_uploader("Complaint CSV", type="csv")
    if uploaded is not None:
        try:
            if uploaded.size > 2_000_000:
                st.error("Use a CSV smaller than 2 MB.")
                return
            frame = pd.read_csv(uploaded)
            if "text" not in frame:
                st.error("The CSV needs a column named text.")
                return
            st.dataframe(frame.head(20), hide_index=True, width="stretch")
            if len(frame) > 20:
                st.warning("Only the first 20 rows will be processed.")
            if st.button("Analyze and save batch", type="primary") and ensure_model(
                backend, model_path
            ):
                progress = st.progress(0.0)
                output: list[dict[str, Any]] = []
                service = get_service(
                    db_path,
                    backend,
                    model_path,
                    backend == "slm" and st.session_state.get("slm_lime", False),
                )
                for index, value in enumerate(frame["text"].head(20)):
                    if pd.isna(value) or not str(value).strip():
                        output.append({"text": "", "error": "Empty narrative"})
                    else:
                        try:
                            output.append(service.analyze(str(value)))
                        except Exception as error:
                            output.append({"text": str(value), "error": str(error)})
                    progress.progress((index + 1) / min(len(frame), 20))
                st.session_state["batch_output"] = output
                st.success(
                    f"Batch complete: {sum('error' not in row for row in output)} complaints saved."
                )
        except (ValueError, pd.errors.ParserError) as error:
            st.error(f"Could not read CSV: {error}")
    if "batch_output" in st.session_state:
        output_frame = pd.DataFrame(st.session_state["batch_output"])
        st.dataframe(output_frame, hide_index=True, width="stretch")
        st.download_button(
            "Export batch results", csv_export(output_frame), "complaintiq_batch.csv", "text/csv"
        )


def main() -> None:
    st.set_page_config(page_title="ComplaintIQ", page_icon="C", layout="wide")
    st.markdown(
        f"<style>{(ROOT / 'assets' / 'style.css').read_text(encoding='utf-8')}</style>", unsafe_allow_html=True
    )
    st.sidebar.title("ComplaintIQ")
    st.sidebar.caption("FINANCIAL COMPLAINT INTELLIGENCE")
    view = st.sidebar.radio(
        "Workspace",
        ["Analyze complaint", "Complaint queue", "Analytics", "Model evidence", "Batch analysis"],
        key="workspace",
    )
    st.sidebar.divider()
    backend, model_path = model_settings()
    st.markdown(
        '<div class="eyebrow">INTELLIGENCE FOR THE NEXT ACTION</div>', unsafe_allow_html=True
    )
    st.title("ComplaintIQ")
    st.caption("A practical workstation for financial complaint classification and triage.")
    db_path = os.environ.get("COMPLAINTIQ_DB_PATH", str(ROOT / "data" / "complaintiq.sqlite3"))
    try:
        if view == "Analyze complaint":
            analyze_view(db_path, backend, model_path)
        elif view == "Complaint queue":
            queue_view(db_path)
        elif view == "Analytics":
            analytics_view(db_path)
        elif view == "Model evidence":
            evidence_view()
        else:
            batch_view(db_path, backend, model_path)
    except Exception as error:
        st.error(f"The workspace could not load: {error}")
    st.divider()
    st.caption(
        "Assignment demo · Classification support for human review · Based on complaint-routing-intelligence (MIT). See THIRD_PARTY_NOTICES.md. Data: historical public CFPB narratives, 990-example demo sample."
    )


if __name__ == "__main__":
    main()
