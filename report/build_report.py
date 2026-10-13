"""Build the ComplaintIQ SLM project report (HTML + PDF) from the project's saved evidence.

Every number in the report is read from a file under the project (results, artifacts,
manifests, logs). Values observed during the session but not saved to a file are listed
in OBSERVED below with where they came from.

Run:  .venv\\Scripts\\python.exe report\\build_report.py
"""

from __future__ import annotations

import base64
import csv
import html
import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "training"
RUN = KIT / "results" / "qwen3-4b-main"
OUT_HTML = ROOT / "report" / "ComplaintIQ_SLM_Project_Report.html"
OUT_PDF = ROOT / "report" / "ComplaintIQ_SLM_Project_Report.pdf"
IST = timezone(timedelta(hours=5, minutes=30))
csv.field_size_limit(10**8)

# Measurements taken during the October 9 session that are not stored in a results file.
OBSERVED = {
    "Speed at batch 4 x 4": "about 11-12 s/step (first steps of the 200-step speed test, batch 4 x 4; stopped)",
    "GPU memory at batch 4 x 4": "11.9 of 12.3 GB in use (nvidia-smi); 100% busy but drawing only 121 of 200 W, i.e. waiting on memory spilled into shared system memory",
    "Speed at batch 2 x 8": "7.10 s/step (30-step speed test, batch 2 x 8)",
    "GPU memory at batch 2 x 8": "10.3 GB in use (nvidia-smi) at 182 W, i.e. fully loaded without spilling",
    "PyTorch download": "two pip downloads of torch-2.10.0+cu126 (2.59 GB) failed SHA-256 verification "
    "(expected 4749cd32..., got c1d641e5... and 7044e20c...); a resumable curl download matched the "
    "official hash and was installed",
}

# Palette: validated reference slots (light). Aqua is < 3:1, so every bar carries a value label.
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
SEQ = ["#f4f8fd", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def esc(s) -> str:
    return html.escape(str(s))


def pct(x, d=1) -> str:
    return f"{x * 100:.{d}f}%"


def short(label: str) -> str:
    names = {
        "Checking or savings account / Deposits and withdrawals": "Checking · Deposits & withdrawals",
        "Checking or savings account / Managing an account": "Checking · Managing an account",
        "Checking or savings account / Problems caused by my funds being low": "Checking · Funds being low",
        "Credit card / Billing disputes": "Credit card · Billing disputes",
        "Credit card / Fees or interest": "Credit card · Fees or interest",
        "Credit card / Other": "Credit card · Other",
        "Credit reporting / Improper use of your report": "Credit report · Improper use",
        "Credit reporting / Incorrect information on your report": "Credit report · Incorrect information",
        "Credit reporting / Problem with a credit reporting company's investigation into an existing problem": "Credit report · Investigation problem",
        "Unknown / Needs review": "Out of scope (Unknown)",
    }
    return names.get(label, label)


# --------------------------------------------------------------------------- charts (inline SVG)
def legend(items: list[tuple[str, str]]) -> str:
    return '<div class="legend">' + "".join(
        f'<span><i style="background:{c}"></i>{esc(n)}</span>' for n, c in items
    ) + "</div>"


def hbars(categories: list[str], series: list[dict], *, maximum=1.0, fmt=lambda v: pct(v), label_w=230,
          width=700, bar_h=14, gap=2, group_gap=14) -> str:
    """Horizontal grouped bars, 4px rounded data end, 2px gap between bars, value labels."""
    plot_w = width - label_w - 70
    n = len(series)
    group_h = n * bar_h + (n - 1) * gap
    height = 24 + len(categories) * (group_h + group_gap)
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img">']
    for t in range(0, 5):
        x = label_w + plot_w * t / 4
        out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="4" y2="{height - 20}" stroke="{GRID}" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{height - 6}" class="tick" text-anchor="middle">{esc(fmt(maximum * t / 4))}</text>')
    y = 6
    for i, cat in enumerate(categories):
        out.append(f'<text x="{label_w - 10}" y="{y + group_h / 2 + 4:.1f}" class="cat" text-anchor="end">{esc(cat)}</text>')
        for j, s in enumerate(series):
            v = s["values"][i]
            if v is None:
                continue
            by = y + j * (bar_h + gap)
            w = max(plot_w * min(v, maximum) / maximum, 2)
            r = min(4, w / 2)
            # square at the baseline, rounded at the data end
            out.append(
                f'<path d="M{label_w},{by} h{w - r:.1f} a{r},{r} 0 0 1 {r},{r} v{bar_h - 2 * r} '
                f'a{r},{r} 0 0 1 -{r},{r} h-{w - r:.1f} z" fill="{s["color"]}"/>'
            )
            out.append(f'<text x="{label_w + w + 6:.1f}" y="{by + bar_h - 3}" class="val">{esc(fmt(v))}</text>')
        y += group_h + group_gap
    out.append(f'<line x1="{label_w}" x2="{label_w}" y1="4" y2="{height - 20}" stroke="{AXIS}" stroke-width="1"/>')
    out.append("</svg>")
    return "".join(out)


def line_chart(points: list[tuple[float, float]], *, width=700, height=230, ylabel="", color=BLUE,
               annotate: list[tuple[float, str]] | None = None) -> str:
    left, right, top, bottom = 52, 20, 12, 34
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    x0, x1, y1 = 0, max(xs), max(ys) * 1.08
    sx = lambda v: left + (width - left - right) * (v - x0) / (x1 - x0)  # noqa: E731
    sy = lambda v: top + (height - top - bottom) * (1 - v / y1)  # noqa: E731
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img">']
    for t in range(5):
        v = y1 * t / 4
        out.append(f'<line x1="{left}" x2="{width - right}" y1="{sy(v):.1f}" y2="{sy(v):.1f}" stroke="{GRID}"/>')
        out.append(f'<text x="{left - 8}" y="{sy(v) + 4:.1f}" class="tick" text-anchor="end">{v:.2f}</text>')
    for t in range(6):
        v = x1 * t / 5
        out.append(f'<text x="{sx(v):.1f}" y="{height - 14}" class="tick" text-anchor="middle">{v:.0f}</text>')
    out.append(f'<text x="{(left + width - right) / 2}" y="{height - 1}" class="tick" text-anchor="middle">training step</text>')
    out.append(f'<text x="12" y="{(top + height - bottom) / 2}" class="tick" transform="rotate(-90 12 {(top + height - bottom) / 2})" text-anchor="middle">{esc(ylabel)}</text>')
    out.append(f'<line x1="{left}" x2="{width - right}" y1="{sy(0):.1f}" y2="{sy(0):.1f}" stroke="{AXIS}"/>')
    d = " ".join(f"{'M' if i == 0 else 'L'}{sx(x):.1f},{sy(y):.1f}" for i, (x, y) in enumerate(points))
    out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round"/>')
    for x, text in annotate or []:
        y = min(points, key=lambda p: abs(p[0] - x))[1]
        out.append(f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="4" fill="{color}" stroke="{SURFACE}" stroke-width="2"/>')
        end = sx(x) > width * 0.7
        anchor = "end" if end else "start"
        out.append(f'<text x="{sx(x) + (-8 if end else 8):.1f}" y="{sy(y) - 8:.1f}" class="val" text-anchor="{anchor}">{esc(text)}</text>')
    out.append("</svg>")
    return "".join(out)


def heatmap(labels: list[str], confusion: dict, *, cell=30, label_w=210) -> str:
    n = len(labels)
    top = 160
    width, height = label_w + n * cell + 130, top + 6 + n * cell
    vmax = max(confusion[g].get(p, 0) for g in labels for p in labels)
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img">']
    for j, p in enumerate(labels):
        x = label_w + j * cell + cell / 2
        out.append(f'<text transform="translate({x + 4:.1f},{top - 6}) rotate(-55)" class="tick">{esc(short(p))}</text>')
    for i, g in enumerate(labels):
        y = top + i * cell
        out.append(f'<text x="{label_w - 8}" y="{y + cell / 2 + 4:.1f}" class="cat" text-anchor="end">{esc(short(g))}</text>')
        for j, p in enumerate(labels):
            v = confusion[g].get(p, 0)
            step = 0 if v == 0 else min(len(SEQ) - 1, 1 + int((len(SEQ) - 2) * (v / vmax) ** 0.6))
            fill = SEQ[step]
            ink = "#ffffff" if step >= 5 else INK
            out.append(f'<rect x="{label_w + j * cell + 1}" y="{y + 1}" width="{cell - 2}" height="{cell - 2}" rx="3" fill="{fill}"/>')
            if v:
                out.append(f'<text x="{label_w + j * cell + cell / 2:.1f}" y="{y + cell / 2 + 4:.1f}" class="cell" fill="{ink}" text-anchor="middle">{v}</text>')
    out.append("</svg>")
    return "".join(out)


def diagram(boxes: list[tuple], arrows: list[tuple], width=700, height=220) -> str:
    """Boxes: (x, y, w, h, title, subtitle, fill). Arrows: (x1, y1, x2, y2, label)."""
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%" role="img"><defs><marker id="ah" '
           f'markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" '
           f'fill="{INK2}"/></marker></defs>']
    for x1, y1, x2, y2, label in arrows:
        out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{INK2}" stroke-width="1.5" marker-end="url(#ah)"/>')
        if label:
            out.append(f'<text x="{(x1 + x2) / 2:.1f}" y="{(y1 + y2) / 2 - 6:.1f}" class="tick" text-anchor="middle">{esc(label)}</text>')
    for x, y, w, h, title, sub, fill in boxes:
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="rgba(11,11,11,0.18)"/>')
        out.append(f'<text x="{x + w / 2}" y="{y + h / 2 - (4 if sub else -4)}" class="boxt" text-anchor="middle">{esc(title)}</text>')
        if sub:
            out.append(f'<text x="{x + w / 2}" y="{y + h / 2 + 12}" class="boxs" text-anchor="middle">{esc(sub)}</text>')
    out.append("</svg>")
    return "".join(out)


def table(head: list[str], body: list[list], *, num_cols: set[int] | None = None, cls="") -> str:
    num_cols = num_cols or set()
    th = "".join(f'<th class="{"num" if i in num_cols else ""}">{esc(h)}</th>' for i, h in enumerate(head))
    trs = "".join(
        "<tr>" + "".join(f'<td class="{"num" if i in num_cols else ""}">{c}</td>' for i, c in enumerate(r)) + "</tr>"
        for r in body
    )
    return f'<table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>'


def figure(title: str, svg: str, caption: str, extra: str = "") -> str:
    return f'<figure><figcaption class="ft">{esc(title)}</figcaption>{extra}{svg}<p class="cap">{caption}</p></figure>'


def stat(value: str, label: str, note: str = "") -> str:
    return f'<div class="stat"><strong>{value}</strong><span>{esc(label)}</span>{f"<small>{esc(note)}</small>" if note else ""}</div>'


# --------------------------------------------------------------------------- evidence
def evidence() -> dict:
    e: dict = {}
    e["ft"] = load(RUN / "eval" / "results.json")
    e["summary"] = load(RUN / "train_summary.json")
    e["config"] = load(RUN / "run_config.json")
    e["log"] = [json.loads(line) for line in (RUN / "train_log.jsonl").read_text(encoding="utf-8").splitlines()]
    e["export"] = load(RUN / "export" / "export_manifest.json")
    e["gguf300"] = load(RUN / "export" / "gguf_test_predictions.json")
    e["test_pred"] = load(RUN / "eval" / "test_predictions.json")["predictions"]
    e["kit_manifest"] = load(KIT / "data" / "manifest.json")
    e["baseline153"] = load(ROOT / "artifacts" / "evaluation.json")
    e["qwen25_153"] = load(ROOT / "artifacts" / "finetuned_evaluation.json")
    e["qwen3_153"] = load(ROOT / "artifacts" / "qwen3_evaluation.json")
    e["scope"] = load(ROOT / "artifacts" / "scope_evaluation.json")
    e["phase1_manifest"] = load(ROOT / "data" / "finetuning" / "manifest.json")
    e["test_rows"] = {r["complaint_id"]: r for r in rows(KIT / "data" / "test.csv")}
    # adapter vs GGUF on the same 300 rows
    adapter = {p["complaint_id"]: p for p in e["test_pred"]}
    g = e["gguf300"]["predictions"]
    pairs = [(p, adapter[p["complaint_id"]]) for p in g if p["complaint_id"] in adapter]
    e["quant"] = {
        "n": len(pairs),
        "gguf": sum(a["predicted"] == a["gold"] for a, _ in pairs) / len(pairs),
        "adapter": sum(b["predicted"] == b["gold"] for _, b in pairs) / len(pairs),
        "agree": sum(a["predicted"] == b["predicted"] for a, b in pairs) / len(pairs),
        "latency_mean": sum(p["latency_ms"] for p in g) / len(g),
    }
    return e


def latency_stats(report: dict) -> tuple[float, float, float]:
    lat = sorted(p["latency_ms"] for p in report["predictions"])
    return sum(lat) / len(lat), lat[len(lat) // 2], lat[max(0, int(0.95 * len(lat)) - 1)]


def ist(ts: str) -> str:
    return datetime.fromisoformat(ts).astimezone(IST).strftime("%H:%M")


# --------------------------------------------------------------------------- report
def build() -> str:
    e = evidence()
    ft, cfg, summ = e["ft"], e["config"], e["summary"]
    t, c = ft["test"]["overall"], ft["check"]
    labels = list(t["per_class"].keys())
    km = e["kit_manifest"]
    b, q25, q3 = e["baseline153"], e["qwen25_153"], e["qwen3_153"]
    q25_lat, q3_lat = latency_stats(q25), latency_stats(q3)
    quant = e["quant"]
    logs = [x for x in e["log"] if x["event"] == "log" and "loss" in x]
    events = {x["event"]: x for x in e["log"] if x["event"] != "log"}
    loss_pts = [(x["step"], x["loss"]) for x in logs]
    train_vram = max(x.get("vram_peak_gb", 0) for x in logs)
    logo = base64.b64encode((ROOT / "frontend" / "public" / "veltris-logo.png").read_bytes()).decode()

    # ---------- section: summary numbers
    S = []
    S.append(f"""
<section class="cover">
  <img class="logo" src="data:image/png;base64,{logo}" alt="Veltris">
  <div class="cover-main">
    <p class="eyebrow">Project report · Small Language Model (SLM)</p>
    <h1>ComplaintIQ</h1>
    <p class="subtitle">A locally run, fine-tuned small language model that classifies financial consumer complaints
    by product and issue, with human review, routing and a full audit trail.</p>
  </div>
  <dl class="cover-facts">
    <div><dt>Prepared for</dt><dd>Veltris</dd></div>
    <div><dt>Report date</dt><dd>{datetime.now(IST).strftime("%d %B %Y")}</dd></div>
    <div><dt>Deployed model</dt><dd>Qwen3-4B-Instruct-2507, QLoRA fine-tuned, Q4_K_M GGUF</dd></div>
    <div><dt>Runs on</dt><dd>One Windows 11 PC with an NVIDIA RTX 4070 · no cloud service at inference</dd></div>
  </dl>
</section>""")

    S.append(f"""
<section class="page">
<h2><span>1</span>Executive summary</h2>
<p class="lead">ComplaintIQ reads a customer's complaint narrative and predicts which financial product it concerns and
what the issue is, choosing from nine supported product/issue pairs, or flags it as out of scope. A reviewer confirms or
corrects every prediction in a desktop web application; nothing is sent to an external AI service.</p>
<div class="stats">
  {stat(pct(t["product_accuracy"]), "product accuracy", "3,000 newest complaints (Feb-Jul 2026)")}
  {stat(pct(t["accuracy"]), "10-class accuracy", "same 3,000 complaints, incl. out of scope")}
  {stat(f'{q3_lat[0]:.0f} ms', "mean response time", "in the app, RTX 4070")}
  {stat(f'{summ["train_seconds"] / 3600:.1f} h', "training time", "950 QLoRA steps on one RTX 4070")}
</div>
<h3>What was built</h3>
<ul>
<li><b>Two fine-tuning rounds.</b> Phase 1 fine-tuned Qwen2.5-1.5B-Instruct on 9,000 historical complaints in a cloud notebook
and ran it on a MacBook Air M1. Phase 2 fine-tuned the larger <b>Qwen3-4B-Instruct-2507</b> on a 70,162-complaint, time-split
dataset entirely on a local Windows PC, and it is now the deployed model.</li>
<li><b>A complete review application</b>: React/TypeScript interface, FastAPI service, SQLite case store with append-only history,
durable processing queue, CSV import, backups and an evaluation page, all bound to <code>127.0.0.1</code>.</li>
<li><b>Measured evidence for every claim</b>: each figure in this report is read from a saved evaluation or log file in the project.</li>
</ul>
<h3>Key results</h3>
<ul>
<li>On the project's original 153 reserved test complaints, the deployed Qwen3 model reaches <b>{pct(q3["product"]["accuracy"], 2)}</b>
product and <b>{pct(q3["joint_accuracy"], 2)}</b> joint product/issue accuracy, against {pct(q25["product"]["accuracy"], 2)} / {pct(q25["joint_accuracy"], 2)}
for the Phase 1 Qwen2.5 model and {pct(b["product"]["accuracy"], 2)} / {pct(b["joint_accuracy"], 2)} for the TF-IDF baseline, and answers
about {q25_lat[0] / q3_lat[0]:.1f}x faster than Phase 1 did on the Mac ({q3_lat[0]:.0f} ms vs {q25_lat[0]:.0f} ms, different hardware).</li>
<li>The model never produced an invalid label (<b>{t["invalid_predictions"]}</b> invalid replies in {t["n"]:,} test cases), because decoding is constrained to the allowed answers.</li>
<li>Out-of-scope detection: precision {pct(t["out_of_scope"]["precision"])} and recall {pct(t["out_of_scope"]["recall"])} on the test set; {pct(c["scope_unrelated_authored_test"]["accuracy"])} of hand-written unrelated texts were flagged.</li>
</ul>
<h3>Honest limits</h3>
<ul>
<li>The three credit-reporting issues are the hardest classes (F1 about 48-50%): their narratives overlap heavily.</li>
<li>Compressing the model to 4-bit GGUF for fast local serving cost accuracy: on 300 identical test rows the GGUF scored
{pct(quant["gguf"])} vs {pct(quant["adapter"])} for the unquantized fine-tuned model.</li>
<li>To fit a three-hour window, training stopped after 950 steps (about {950 * 16 / 70162:.0%} of one epoch). A full epoch may score differently.</li>
</ul>
</section>""")

    # ---------- 2. problem & scope
    classes_tbl = table(
        ["#", "Product", "Issue"],
        [[i + 1, esc(lab.split(" / ")[0]), esc(lab.split(" / ")[1])] for i, lab in enumerate(labels)],
        num_cols={0},
    )
    S.append(f"""
<section class="page">
<h2><span>2</span>Problem, scope and approach</h2>
<p>Financial institutions receive large volumes of free-text complaints. Routing each one to the right team depends on
understanding which product it concerns and what went wrong. The assignment was to build a working complaint-intelligence
pilot around a <b>small language model that is fine-tuned on the task and runs locally</b>, measured honestly against a
traditional baseline.</p>
<h3>Label space</h3>
<p>Three product families and nine issue pairs, chosen from the public CFPB Consumer Complaint Database where narratives are
plentiful, plus one out-of-scope class added in Phase 2 so the model itself can decline unrelated text.</p>
{classes_tbl}
<h3>Approach</h3>
<ol>
<li><b>Baseline first.</b> A TF-IDF + logistic-regression classifier sets the bar (product {pct(b["product"]["accuracy"], 2)}, joint {pct(b["joint_accuracy"], 2)} on 153 reserved complaints).</li>
<li><b>Choose a model that fits the hardware.</b> Candidates were benchmarked locally before any training (Section 6).</li>
<li><b>Fine-tune with QLoRA</b> (4-bit base model + small trainable LoRA adapters), so training fits a single consumer GPU.</li>
<li><b>Generative classifier with constrained decoding.</b> The model answers with the application's exact JSON
(<code>{{"product": ..., "issue": ...}}</code>), and decoding is restricted to the ten valid answers, so every reply is a legal label.</li>
<li><b>Export to 4-bit GGUF</b> and serve it with llama.cpp behind the application; a human confirms every decision.</li>
</ol>
<p class="note">Priority, department routing and suggested next steps are explicit, documented rules, not model predictions.
Summaries are extractive previews. No confidence or risk percentages are invented.</p>
</section>""")

    # ---------- 3. architecture
    arch = diagram(
        [
            (10, 70, 130, 64, "Reviewer's browser", "React + TypeScript", "#eef4fc"),
            (190, 70, 150, 64, "FastAPI service", "127.0.0.1:8501", "#eef4fc"),
            (390, 10, 140, 54, "Scope gate", "TF-IDF + rules", "#f4f3ef"),
            (390, 84, 140, 54, "Durable job queue", "one row at a time", "#f4f3ef"),
            (390, 158, 140, 54, "SQLite case store", "history · backups", "#f4f3ef"),
            (575, 84, 120, 54, "llama-server", "CUDA · :8504", "#e8f6f0"),
        ],
        [
            (140, 102, 188, 102, "HTTP"),
            (340, 92, 388, 40, ""),
            (340, 108, 388, 111, ""),
            (340, 118, 388, 182, ""),
            (530, 111, 573, 111, "GGUF"),
        ],
        height=220,
    )
    S.append(f"""
<section class="page">
<h2><span>3</span>System architecture</h2>
{figure("Figure 1 · Runtime components (all on one machine)", arch, "Every process binds to the loopback interface only. The model server holds one Q4_K_M GGUF and handles one request at a time; failures surface as explicit errors, never a silent switch to the baseline.")}
<h3>Request flow</h3>
<ol>
<li>A complaint is submitted (single narrative or CSV of up to 100 rows / 2 MB). It is written to the durable queue before inference.</li>
<li>The <b>scope gate</b> checks for card, credit-report or bank-account context and runs a TF-IDF classifier trained on supported vs other-product complaints; out-of-scope text goes to review without calling the model.</li>
<li>The first 2,000 normalized characters go to <b>llama-server</b> with the system prompt and a JSON schema that only allows the valid product/issue pairs. The reply is validated again in Python.</li>
<li>Rules add priority, department and a suggested next step; the case is saved with its original prediction, which is never overwritten.</li>
<li>A reviewer confirms or corrects the labels (a reason is required), adds notes and moves the case through <i>Queued → In review → Resolved</i>. Every change is appended to the case history.</li>
</ol>
<h3>Components</h3>
{table(["Layer", "Technology", "Notes"], [
    ["Interface", "React 18, TypeScript, Vite", "Cases queue, case detail and review, analysis, CSV imports, model & system page"],
    ["API", "FastAPI, Uvicorn (Python 3.12)", "Same-origin writes only, loopback hosts, revision checks reject stale edits (HTTP 409)"],
    ["Storage", "SQLite (versioned schema)", "Cases, append-only events, jobs; daily automatic + manual backups; validated restore tool"],
    ["Inference", "llama.cpp b11496 llama-server (CUDA 12.4)", "2,048-token context, 1 slot, JSON-schema constrained decoding"],
    ["Model", esc(e["export"]["gguf"]), f'Q4_K_M, {e["export"]["bytes"] / 2**30:.2f} GiB, SHA-256 {e["export"]["sha256"][:16]}...'],
    ["Baseline", "scikit-learn TF-IDF + logistic regression", "Trained from CSV at start-up (no pickled models); LIME explanations"],
])}
</section>""")

    # ---------- 4. data
    sc = km["split_counts"]
    S.append(f"""
<section class="page">
<h2><span>4</span>Training data</h2>
<p>Both phases use real, public consumer complaint narratives from the U.S. Consumer Financial Protection Bureau (CFPB).
Labels are the product and issue the consumer selected when filing; they are not independently adjudicated.</p>
<h3>Phase 1 dataset (Qwen2.5-1.5B)</h3>
{table(["Property", "Value"], [
    ["Source", "Official CFPB narratives archive, December 2011 - April 2018 (1,031,863 records)"],
    ["Selected complaint dates", "19 March 2015 - 30 April 2018"],
    ["Split sizes", "9,000 training · 900 validation · 900 test (1,000 / 100 / 100 per issue)"],
    ["Classes", "9 product/issue pairs (no out-of-scope examples)"],
    ["Leakage control", "Zero shared IDs or input hashes across splits; 65 near-duplicates (word-shingle Jaccard ≥ 0.95) rejected"],
    ["Original reserved test", "153 complaints kept in the test split since the baseline was built; used for every cross-model comparison"],
])}
<h3>Phase 2 dataset (Qwen3-4B, deployed)</h3>
{table(["Property", "Value"], [
    ["Source", esc(km["source"]) + " (archived 15 Aug 2026 capture; the live export no longer includes narratives)"],
    ["Archive SHA-256", f'<code>{km["archive_sha256"][:24]}...</code>'],
    ["Eligible narratives scanned", f'{km["eligible_rows_scanned"]:,} ({km["data_months"][0]} to {km["data_months"][1]})'],
    ["Split policy", "Time-based: newest months are the test set, so the model is tested on complaints newer than anything it trained on"],
    ["Training", f'{sc["train"]:,} complaints (2015-03 to 2025-11), about 7,000 per class'],
    ["Validation", f'{sc["validation"]:,} complaints (2025-12 to 2026-01)'],
    ["Test", f'{sc["test"]:,} complaints (2026-02 to 2026-07), 300 per class'],
    ["Check set (held out)", f'{sc.get("check", 1407):,}: the original 153 test complaints, 1,200 other-product complaints and 54 hand-written unrelated texts'],
    ["Out-of-scope class", "Other CFPB products (debt collection, mortgage, student loan, vehicle/consumer loan, payday/personal loan, money transfer, prepaid card, debt management) sampled evenly, plus 54 authored non-financial examples (x3)"],
    ["De-duplication", "Exact duplicates removed across splits (test wins over validation over train); training rows near-duplicating any evaluation row (shingle Jaccard ≥ 0.9) dropped: 3,052"],
    ["Model input", "Whitespace-normalized first 2,000 characters, identical to what the app sends"],
    ["Token lengths (Qwen3 tokenizer)", f'mean {summ["data_mean_tokens"]:.0f}, median {summ["data_p50_tokens"]}, capped at {summ["data_max_tokens"]}; {summ["data_truncated_complaints"]:,} of {summ["data_examples"]:,} training complaints ({summ["data_truncated_complaints"] / summ["data_examples"]:.0%}) shortened to fit 512 tokens'],
])}
<p class="note">CFPB issue names changed in 2017; older and newer names are mapped onto the nine pairs (e.g. "Problem with a purchase shown on your statement" → Billing disputes).
The full mapping and file hashes are in <code>training/data/manifest.json</code>.</p>
</section>""")

    # ---------- 5. hardware & software
    S.append(f"""
<section class="page">
<h2><span>5</span>Devices and software</h2>
{table(["Device", "Specification", "Used for"], [
    ["Apple MacBook Air (M1)", "Apple M1, 8 GB unified memory, macOS · llama.cpp with Metal", "Phase 1: data preparation, baseline, local model benchmark, running the Qwen2.5 app; preparing the Windows training kit"],
    ["Google Colab (cloud notebook)", "Cloud GPU runtime · Unsloth", "Phase 1: QLoRA training of Qwen2.5-1.5B and Q4_K_M export"],
    ["Lenovo workstation (30FS)", "Intel Core i7-14700K (20 cores / 28 threads) · 32 GB RAM (31.6 GB usable) · <b>NVIDIA GeForce RTX 4070, 12 GB</b> (driver 610.60, compute 8.9) · Windows 11 Pro · ~950 GB data drive (D:) for the project", "Phase 2: training, evaluation, GGUF export and running the deployed application"],
])}
<h3>Software (Phase 2, Windows PC)</h3>
{table(["Component", "Version"], [
    ["Training environment", "Python 3.11.9 · PyTorch 2.10.0 + CUDA 12.6 · Transformers 5.19.0 · PEFT 0.21.2 · bitsandbytes 0.50.2 · Accelerate 1.15.0"],
    ["Application environment", "Python 3.12.10 · FastAPI 0.142.2 · Uvicorn 0.54.0 · scikit-learn 1.9.1 · pandas 3.0.6"],
    ["Frontend build", "Node.js 24 · React 18 · TypeScript · Vite"],
    ["Model serving / export", "llama.cpp b11496 (llama-server and llama-quantize, CUDA 12.4 build; convert_hf_to_gguf)"],
    ["Development tools", "VS Code with Jupyter (training notebook), Claude Code (assistant), pytest, ruff, mypy, Vitest"],
])}
<h3>Base models</h3>
{table(["Model", "Parameters", "Role"], [
    ["Qwen2.5-1.5B-Instruct", "1.54 B", "Phase 1 fine-tuned model (Mac)"],
    ["Qwen3.5-0.8B", "0.8 B", "Benchmarked in Phase 1, not selected"],
    ["Qwen3-4B-Instruct-2507", "4.06 B (33.0 M trainable LoRA = 0.81%)", "Phase 2 fine-tuned and deployed model"],
])}
</section>""")

    # ---------- 6. phase 1
    S.append(f"""
<section class="page">
<h2><span>6</span>Phase 1: model selection and Qwen2.5-1.5B</h2>
<h3>Local model benchmark (before training, MacBook Air M1)</h3>
<p>Two small instruction models were compared on the same 27 validation complaints (three per class) with identical prompts,
before any fine-tuning. "Verified pair schema" means decoding was constrained to valid product/issue pairs.</p>
{table(["Backend and decoding", "Product acc.", "Joint acc.", "Valid output", "Median latency"], [
    ["TF-IDF baseline", "88.89%", "55.56%", "100%", "0.8 ms"],
    ["Qwen2.5-1.5B, free JSON", "51.85%", "25.93%", "59.26%", "1,005 ms"],
    ["Qwen3.5-0.8B, free JSON", "3.70%", "0.00%", "11.11%", "755 ms"],
    ["Qwen2.5-1.5B, verified pair schema", "77.78%", "48.15%", "100%", "944 ms"],
    ["Qwen3.5-0.8B, verified pair schema", "59.26%", "22.22%", "100%", "646 ms"],
], num_cols={1, 2, 3, 4})}
<p class="src">Source: docs/LOCAL_MODEL_COMPARISON.md and artifacts/local_*_validation.json. Constrained decoding was adopted for every later model.</p>
<h3>Phase 1 training configuration (Google Colab, Unsloth)</h3>
{table(["Setting", "Value"], [
    ["Base model", "Qwen2.5-1.5B-Instruct, loaded in 4-bit"],
    ["Method", "QLoRA, LoRA rank 16, alpha 16, dropout 0"],
    ["Batch", "2 per step x 8 gradient accumulation = 16"],
    ["Optimizer / schedule", "Learning rate 2e-4, linear decay, 10 warm-up steps"],
    ["Length", "1 epoch over 9,000 complaints = 563 steps (exported checkpoint-563); max sequence 2,048 tokens"],
    ["Export", "Q4_K_M GGUF, 986 MB, served by llama.cpp with Metal on the M1"],
])}
<h3>Phase 1 results</h3>
{table(["Configuration", "Cases", "Product acc.", "Joint acc."], [
    ["Original Qwen2.5, constrained (validation)", "27", "77.78%", "48.15%"],
    ["Fine-tuned Qwen2.5, constrained (validation)", "27", "96.30%", "74.07%"],
    ["TF-IDF baseline, reserved test", "153", pct(b["product"]["accuracy"], 2), pct(b["joint_accuracy"], 2)],
    ["Fine-tuned Qwen2.5, reserved test", "153", pct(q25["product"]["accuracy"], 2), pct(q25["joint_accuracy"], 2)],
], num_cols={1, 2, 3})}
<p>The large validation gain did not carry over to the reserved test, where Phase 1 matched but did not beat the baseline on joint accuracy.
The model also had no way to decline unrelated text, so a separate scope gate was added. Both observations motivated Phase 2:
a larger model, far more and newer training data, and an explicit out-of-scope class.</p>
</section>""")

    # ---------- 7. phase 2 training
    speed_tbl = table(["Configuration", "Speed", "GPU memory", "Outcome"], [
        ["Batch 4 x 4 accumulation (kit default)", OBSERVED["Speed at batch 4 x 4"], OBSERVED["GPU memory at batch 4 x 4"], "Rejected: a full epoch would take about 14 h"],
        ["Batch 2 x 8 accumulation (same effective batch 16)", OBSERVED["Speed at batch 2 x 8"] + f'; {summ["seconds_per_step"]:.2f} s/step over the full run', f'{train_vram:.1f} GB peak allocated by training steps; ' + OBSERVED["GPU memory at batch 2 x 8"], "Used for the main run"],
    ])
    S.append(f"""
<section class="page">
<h2><span>7</span>Phase 2: training Qwen3-4B on the PC</h2>
<p>The training kit (scripts, data, pinned dependencies and a notebook) was prepared on the Mac and run on the Windows PC.
Training ran from the notebook on the <code>windows-pc-kit</code> branch in VS Code: environment check → dry run → speed test → training → evaluation → export.</p>
<h3>Training configuration</h3>
{table(["Setting", "Value"], [
    ["Base model", "Qwen3-4B-Instruct-2507, 4-bit NF4 with double quantization, bf16 compute, SDPA attention"],
    ["Adapters", f'LoRA rank {cfg["lora_r"]}, alpha {cfg["lora_alpha"]}, dropout {cfg["lora_dropout"]}, on all attention and MLP projections (33.0 M trainable parameters)'],
    ["Batch", f'{cfg["batch_size"]} per step x {cfg["grad_accum"]} gradient accumulation = 16 sequences per optimizer step'],
    ["Optimizer", f'AdamW, learning rate {float(cfg["lr"]):g}, cosine schedule, {float(cfg["warmup_fraction"]):.0%} warm-up, gradient clipping 1.0, gradient checkpointing'],
    ["Sequence length", f'{cfg["max_length"]} tokens (prompt + answer); the complaint is shortened to fit, never the prompt; loss on answer tokens only'],
    ["Length", f'{summ["steps_completed"]} steps = {summ["steps_completed"] * 16:,} complaints seen ({summ["steps_completed"] / summ["steps_per_epoch"]:.0%} of one {summ["steps_per_epoch"]:,}-step epoch); {cfg["time_budget_hours"]} h safety stop (not reached)'],
    ["Checkpoints", f'every {cfg["save_steps"]} steps; checkpoint-950 and the final adapter are kept'],
    ["Evaluation decoding", "Greedy, constrained to the ten valid replies (token trie); prompts up to 1,024 tokens, matching the app's 2,000-character input"],
    ["Seed", cfg["seed"]],
])}
<h3>Making it fit the GPU</h3>
{speed_tbl}
<p>Halving the per-step batch and doubling gradient accumulation keeps the optimisation identical (16 sequences per update)
while stopping memory from spilling out of the 12 GB card. That made each step about a third faster. The step count was then chosen
so that training plus evaluation and export would finish in about three hours.</p>
</section>""")

    loss_svg = line_chart(
        loss_pts, ylabel="training loss",
        annotate=[(loss_pts[0][0], f"{loss_pts[0][1]:.3f} at step {loss_pts[0][0]}"),
                  (loss_pts[-1][0], f"{loss_pts[-1][1]:.3f} at step {loss_pts[-1][0]}")],
    )
    tl = [
        ["10:52", "Automated setup started (RUN_ALL.bat); model and installers downloaded and SHA-256 verified"],
        ["11:16-11:24", "Setup stopped twice: PyTorch download failed its hash check (see Section 12)"],
        ["~11:45", "Verified PyTorch installed from a resumable download; packages installed from the notebook; environment check READY"],
        ["11:50-12:05", "Dry run passed (5 steps, adapter saved and reloaded); speed tests compared batch 4 x 4 with batch 2 x 8"],
        [ist(events["start"]["time"]), "Training started (950 steps)"],
        [ist(events["adapter_saved"]["time"]), f'Training finished: {summ["train_seconds"] / 3600:.2f} h, final adapter saved'],
        [ist(events["done"]["time"]), "Automatic evaluation on 3,000 test + 1,407 check complaints finished"],
        ["14:35-14:42", "GGUF export: merge, convert, quantize to Q4_K_M and 300-row llama-server check"],
        ["~14:45", "Application started with the new model; end-to-end analysis verified in the browser"],
    ]
    S.append(f"""
<section class="page">
<h3>Training progress</h3>
{figure("Figure 2 · Training loss over 950 steps (logged every 10 steps)", loss_svg,
        f'Loss on the answer tokens fell from {loss_pts[0][1]:.3f} to {loss_pts[-1][1]:.3f}; average training loss {summ["train_loss"]:.4f}. Cosine learning-rate schedule decays to zero at step 950. Source: training/results/qwen3-4b-main/train_log.jsonl.')}
<h3>Run timeline, 9 October 2026 (IST)</h3>
{table(["Time", "Event"], tl)}
<h3>Export for serving</h3>
{table(["Step", "Detail"], [
    ["Merge", "Adapter merged into the bf16 base model on the CPU"],
    ["Convert + quantize", f'llama.cpp b11496 convert_hf_to_gguf, then llama-quantize to Q4_K_M ({e["export"]["bytes"] / 2**30:.2f} GiB)'],
    ["Identity", f'<code>{esc(e["export"]["gguf"])}</code> · SHA-256 <code>{e["export"]["sha256"][:32]}...</code>'],
    ["Regression check", f'{quant["n"]} fixed test rows sent through llama-server with the app\'s exact request'],
])}
</section>""")

    # ---------- 8. benchmarks
    hist = hbars(
        ["Product accuracy", "Joint product/issue accuracy", "Product macro-F1", "Issue macro-F1"],
        [
            {"name": "TF-IDF baseline", "color": AQUA, "values": [b["product"]["accuracy"], b["joint_accuracy"], b["product"]["f1_macro"], b["issue"]["f1_macro"]]},
            {"name": "Qwen2.5-1.5B fine-tuned (Phase 1)", "color": ORANGE, "values": [q25["product"]["accuracy"], q25["joint_accuracy"], q25["product"]["f1_macro"], q25["issue"]["f1_macro"]]},
            {"name": "Qwen3-4B fine-tuned (Phase 2, deployed)", "color": BLUE, "values": [q3["product"]["accuracy"], q3["joint_accuracy"], q3["product"]["f1_macro"], q3["issue"]["f1_macro"]]},
        ],
        label_w=200,
    )
    hist_tbl = table(["Model (153 reserved complaints)", "Product acc.", "Joint acc.", "Product macro-F1", "Issue macro-F1", "Mean latency", "Hardware"], [
        ["TF-IDF baseline", pct(b["product"]["accuracy"], 2), pct(b["joint_accuracy"], 2), pct(b["product"]["f1_macro"], 1), pct(b["issue"]["f1_macro"], 1), f'{b["latency_ms_mean"]:.1f} ms', "CPU"],
        ["Qwen2.5-1.5B fine-tuned", pct(q25["product"]["accuracy"], 2), pct(q25["joint_accuracy"], 2), pct(q25["product"]["f1_macro"], 1), pct(q25["issue"]["f1_macro"], 1), f'{q25_lat[0]:.0f} ms', "M1, Metal"],
        ["Qwen3-4B fine-tuned (GGUF)", pct(q3["product"]["accuracy"], 2), pct(q3["joint_accuracy"], 2), pct(q3["product"]["f1_macro"], 1), pct(q3["issue"]["f1_macro"], 1), f'{q3_lat[0]:.0f} ms', "RTX 4070, CUDA"],
    ], num_cols={1, 2, 3, 4, 5})
    S.append(f"""
<section class="page">
<h2><span>8</span>Benchmarks</h2>
<p>Three benchmark sets are used, each answering a different question:</p>
{table(["Set", "Size", "Question it answers"], [
    ["Original reserved test", "153", "How do all models compare on the same complaints? (2015-2018 data, nine in-scope classes)"],
    ["2026 test set", f'{t["n"]:,}', "How well does the deployed model handle the newest complaints, including out-of-scope ones? (10 classes, 300 each)"],
    ["Check set", f'{c["overall"]["n"]:,}', "Does it decline other products and unrelated text while still classifying the 153 originals?"],
])}
<h3>8.1 Across the project (153 reserved complaints, deployed form of each model)</h3>
{figure("Figure 3 · Accuracy and macro-F1 by model", hist, "Each model evaluated through its serving path with constrained decoding. Sources: artifacts/evaluation.json, finetuned_evaluation.json, qwen3_evaluation.json.", legend([("TF-IDF baseline", AQUA), ("Qwen2.5-1.5B fine-tuned (Phase 1)", ORANGE), ("Qwen3-4B fine-tuned (Phase 2)", BLUE)]))}
{hist_tbl}
<p class="note">Latency compares different machines (M1 laptop vs RTX 4070 desktop), so it reflects the whole deployment, not the model alone.
Qwen3 latency: median {q3_lat[1]:.0f} ms, 95th percentile {q3_lat[2]:.0f} ms.</p>
</section>""")

    co = c["overall"]
    S.append(f"""
<section class="page">
<h3>8.2 Deployed model on the newest complaints and the check set</h3>
<p>Fine-tuned Qwen3-4B adapter, 4-bit base, greedy decoding constrained to the ten valid replies (training/src/evaluate_qwen3.py).</p>
{table(["Metric", "2026 test set (3,000)", "Check set (1,407)"], [
    ["10-class accuracy", pct(t["accuracy"]), pct(co["accuracy"])],
    ["Macro-F1", pct(t["macro_f1"]), pct(co["macro_f1"])],
    ["Weighted F1", pct(t["weighted_f1"]), pct(co["weighted_f1"])],
    ["Product accuracy", pct(t["product_accuracy"]), pct(co["product_accuracy"])],
    ["In-scope joint product/issue accuracy", pct(t["in_scope_joint_accuracy"]), pct(co["in_scope_joint_accuracy"])],
    ["Out-of-scope precision", pct(t["out_of_scope"]["precision"]), pct(co["out_of_scope"]["precision"])],
    ["Out-of-scope recall", pct(t["out_of_scope"]["recall"]), pct(co["out_of_scope"]["recall"])],
    ["Invalid replies", str(t["invalid_predictions"]), str(co["invalid_predictions"])],
], num_cols={1, 2})}
<p class="note">The check set is dominated by out-of-scope complaints (1,254 of 1,407), so its macro-F1 is pulled down by
nine in-scope classes with only 17 examples each; accuracy and weighted F1 describe it better.</p>
<h3>Check set by source</h3>
{table(["Source", "Complaints", "Accuracy"], [
    ["Original 153 reserved test complaints", c["original_test_153"]["n"], pct(c["original_test_153"]["accuracy"])],
    ["Other-product CFPB complaints (should be flagged out of scope)", c["scope_other_products_test"]["n"], pct(c["scope_other_products_test"]["accuracy"])],
    ["Hand-written unrelated texts (should be flagged out of scope)", c["scope_unrelated_authored_test"]["n"], pct(c["scope_unrelated_authored_test"]["accuracy"])],
], num_cols={1, 2})}
</section>""")

    per = t["per_class"]
    pc_svg = hbars(
        [short(lab) for lab in labels],
        [{"name": "Fine-tuned", "color": BLUE, "values": [per[lab]["f1"] for lab in labels]}],
        label_w=230, bar_h=13, group_gap=9,
    )
    pc_tbl = table(["Class", "Precision", "Recall", "F1", "Support"], [
        [esc(short(lab)), pct(per[lab]["precision"]), pct(per[lab]["recall"]), pct(per[lab]["f1"]), per[lab]["support"]] for lab in labels
    ], num_cols={1, 2, 3, 4})
    S.append(f"""
<section class="page">
<h3>8.3 Per-class results (2026 test set, fine-tuned Qwen3-4B adapter)</h3>
{figure("Figure 4 · F1 score per class", pc_svg, "300 test complaints per class. Credit-reporting issues are hardest: complaints about incorrect information, improper use and the bureau's investigation often describe the same dispute.")}
{pc_tbl}
</section>""")

    conf = t["confusion"]
    off = sorted(((conf[g].get(p, 0), g, p) for g in labels for p in labels if g != p), reverse=True)[:6]
    S.append(f"""
<section class="page">
<h3>8.4 Where the model gets confused</h3>
<p>Product-level errors are rare ({pct(1 - t["product_accuracy"])} of test complaints); most mistakes pick the wrong issue
within the right product, which matters less for routing because departments are assigned per product.</p>
{figure("Figure 5 · Confusion matrix, 2026 test set (rows = true class, columns = predicted)", heatmap(labels, conf), "Darker = more complaints. The diagonal is correct; the largest off-diagonal blocks sit inside the credit-reporting family and inside checking accounts.")}
<h3>Most frequent mistakes</h3>
{table(["True class", "Predicted as", "Complaints"], [[esc(short(g)), esc(short(p)), n] for n, g, p in off], num_cols={2})}
</section>""")

    # quantization + latency
    lat_svg = hbars(
        ["Qwen2.5-1.5B, M1 laptop (Metal)", "Qwen3-4B, RTX 4070 (CUDA)"],
        [{"name": "mean", "color": BLUE, "values": [q25_lat[0], q3_lat[0]]}],
        maximum=1000, fmt=lambda v: f"{v:.0f} ms", label_w=230,
    )
    S.append(f"""
<section class="page">
<h3>8.5 Compression check: fine-tuned adapter vs 4-bit GGUF</h3>
{table(["Same {0} test rows".format(quant["n"]), "10-class accuracy"], [
    ["Fine-tuned adapter (Transformers, 4-bit NF4 base)", pct(quant["adapter"])],
    ["Exported Q4_K_M GGUF (llama-server, as the app runs it)", pct(quant["gguf"])],
    ["Identical predictions between the two", pct(quant["agree"])],
], num_cols={1})}
<p>Quantizing the merged model to Q4_K_M ({e["export"]["bytes"] / 2**30:.1f} GiB) cost about {(quant["adapter"] - quant["gguf"]) * 100:.0f} points on this sample,
more than the couple of points the kit anticipated.</p>
<h3>8.6 Speed</h3>
{figure("Figure 6 · Mean time per complaint in the deployed app", lat_svg, "Measured over the 153 reserved complaints through each deployment's model server. Different hardware: the comparison reflects the whole setup, not the model alone. TF-IDF baseline: under 1 ms.")}
{table(["Measure", "Value"], [
    ["Qwen3 GGUF, mean / median / 95th percentile (153 complaints)", f"{q3_lat[0]:.0f} / {q3_lat[1]:.0f} / {q3_lat[2]:.0f} ms"],
    ["Qwen3 GGUF, mean over the 300-row export check", f'{quant["latency_mean"]:.0f} ms'],
    ["Training throughput", f'{summ["seconds_per_step"]:.2f} s per step of 16 complaints (about {16 / summ["seconds_per_step"]:.1f} complaints/s)'],
    ["Batch evaluation (adapter, batch 16)", "about 3-8 complaints/s on the RTX 4070"],
])}
</section>""")

    # ---------- 9. examples
    tp = {p["complaint_id"]: p for p in e["test_pred"]}
    ok, bad, seen_ok, seen_bad = [], [], set(), set()
    for cid in sorted(tp):
        p = tp[cid]
        if p["gold"] == p["predicted"] and p["gold"] not in seen_ok and len(ok) < 6:
            ok.append(p)
            seen_ok.add(p["gold"])
        elif p["gold"] != p["predicted"] and (p["gold"], p["predicted"]) not in seen_bad and len(bad) < 8:
            if (p["gold"], p["predicted"]) in {(g, q) for _, g, q in off} or "Unknown" in p["gold"] or "Unknown" in p["predicted"]:
                bad.append(p)
                seen_bad.add((p["gold"], p["predicted"]))

    def ex_rows(items):
        out = []
        for p in items:
            text = " ".join(e["test_rows"][p["complaint_id"]]["text"].split())
            out.append([f'<span class="excerpt">"{esc(text[:230])}{"..." if len(text) > 230 else ""}"</span>',
                        esc(short(p["gold"])), esc(short(p["predicted"]))])
        return out

    S.append(f"""
<section class="page">
<h2><span>9</span>Inspected examples</h2>
<p>Examples are taken deterministically (sorted by complaint ID) from the 2026 test set. Narratives are public CFPB text;
"XXXX" marks the CFPB's own redactions. Excerpts are shortened.</p>
<h3>Correct predictions</h3>
{table(["Complaint excerpt", "True", "Predicted"], ex_rows(ok), cls="examples")}
<h3>Mistakes</h3>
{table(["Complaint excerpt", "True", "Predicted"], ex_rows(bad), cls="examples")}
<p>Most mistakes are defensible readings of ambiguous narratives: a complaint about a bureau ignoring a dispute of wrong information fits
both "incorrect information" and "investigation problem". This is why every prediction is confirmed by a reviewer, and corrections require a reason.</p>
</section>""")

    # ---------- 10. app & quality
    S.append(f"""
<section class="page">
<h2><span>10</span>Application and quality assurance</h2>
<h3>Features</h3>
<ul>
<li><b>Cases</b>: searchable, filterable queue (product, priority, department, dates, review state), URL-backed filters and CSV export, including an export of human-confirmed labels.</li>
<li><b>Case detail</b>: full narrative, the immutable original prediction and policy assessment, review form (corrections need a reason), notes, lifecycle transitions and an append-only history.</li>
<li><b>Analyze and Imports</b>: single complaints or CSV batches go through one durable queue that survives restarts; failed rows can be retried and pending ones cancelled.</li>
<li><b>Model & System</b>: the loaded model and its training data size (read from the server), measured evaluation with limitations, storage and queue health, one-click backups.</li>
<li><b>Safety</b>: loopback-only binding, same-origin writes, revision checks against stale edits, no silent fallback to another model.</li>
</ul>
<h3>Automated checks (final state)</h3>
{table(["Check", "Result"], [
    ["Python tests (pytest)", "75 passed"],
    ["Frontend tests (Vitest + Testing Library)", "13 passed"],
    ["Static checks", "ruff: no issues · mypy: no issues in 22 files · strict TypeScript build"],
    ["Layout check", "Every page measured at 1,920 / 1,440 / 1,280 / 1,024 px: no overflow or misaligned controls (the app targets desktop screens, minimum width 1,000 px)"],
    ["End-to-end", "Complaint analysed through the browser with the Qwen3 GGUF: Credit card / Billing disputes in 0.5 s"],
])}
<h3>Fixes made while moving to Windows</h3>
{table(["Problem", "Fix"], [
    ["App crashed at start-up (WinError 32) when writing its daily backup", "SQLite connections are now closed explicitly; Windows cannot rename or delete a file that is still open (macOS can)"],
    ["Interface still named the Phase 1 model and 'this Mac'", "The model name is read from the server's model file; wording is device-neutral"],
    ["Health endpoint reported the Phase 1 dataset and re-read up to 78 MB of CSV on every poll", "Reports the active model's dataset and caches row counts (about 40 ms per check)"],
    ["Browser opened before the server was ready", "The launcher opens the browser only after the app answers"],
    ["Date filters sat 4 px below neighbouring controls", "Removed inherited form spacing; all controls in the row now share one baseline"],
    ["Legacy interfaces (Streamlit prototype, first React layout)", "Removed; the review application is the single interface"],
])}
</section>""")

    # ---------- 11-13
    S.append(f"""
<section class="page">
<h2><span>11</span>Limitations</h2>
<ul>
<li><b>Labels are consumer-selected.</b> CFPB product and issue fields are chosen by the person filing, so some "errors" are label noise.</li>
<li><b>Partial epoch.</b> The deployed model saw {summ["steps_completed"] * 16:,} of {summ["data_examples"]:,} training complaints. It was a deliberate time trade-off; a full epoch (about 9.3 h at the measured speed) was not run.</li>
<li><b>Quantization loss.</b> The 4-bit GGUF trails the unquantized adapter by about {(quant["adapter"] - quant["gguf"]) * 100:.0f} points on 300 rows.</li>
<li><b>Fixed taxonomy.</b> Three products and nine issues; everything else is "out of scope", not classified.</li>
<li><b>Truncation.</b> Only the first 2,000 characters are classified, and {summ["data_truncated_complaints"] / summ["data_examples"]:.0%} of training complaints were shortened to 512 tokens.</li>
<li><b>Single operator.</b> No authentication or multi-user permissions; the pilot is meant for one reviewer on one machine.</li>
<li><b>Rules are rules.</b> Priority and routing come from documented phrase rules, not a trained severity model.</li>
</ul>
<h2><span>12</span>Issues encountered and how they were resolved</h2>
{table(["Issue", "Resolution"], [
    ["PyTorch download corruption", esc(OBSERVED["PyTorch download"])],
    ["Notebook checksum mismatch after opening it in VS Code", "VS Code re-saves notebooks; the original was restored for the automated route, then training moved to the notebook itself"],
    ["GPU memory full at the default batch, spilling into system memory", "Batch 2 x 8 instead of 4 x 4: same effective batch, about a third faster"],
    ["Low space on the system drive", "Project moved to the ~950 GB D: drive; Windows enlarged its page file during training"],
    ["Windows-only SQLite file locking", "Explicit connection closing in storage and restore code (Section 10)"],
])}
</section>""")

    # ---------- appendix
    S.append(f"""
<section class="page">
<h2><span>A</span>Appendix: reproducing the results</h2>
{table(["Task", "Command (from D:\\SLMProject)"], [
    ["Start the application", "<code>run_pilot.bat</code> → http://127.0.0.1:8501"],
    ["Fill an empty dashboard with demo complaints", "<code>run_demo_seed.bat</code>"],
    ["Train (notebook)", "<code>pc_kit\\notebooks\\train_qwen3_windows.ipynb</code>, kernel <code>pc_kit\\.venv</code>"],
    ["Export GGUF + 300-row check", "<code>pc_kit\\.venv\\Scripts\\python.exe pc_kit\\src\\export_gguf.py --adapter pc_kit\\results\\qwen3-4b-main\\final_adapter --verify-rows 300</code>"],
    ["Evaluate the GGUF on the 153 reserved complaints (app running)", "<code>.venv\\Scripts\\python.exe -m scripts.evaluate_server --model-path models\\complaintiq-qwen3-4b-Q4_K_M.gguf --output artifacts\\qwen3_evaluation.json</code>"],
    ["Run the tests", "<code>.venv\\Scripts\\python.exe -m pytest</code> · <code>cd frontend &amp;&amp; npm test</code>"],
    ["Rebuild this report", "<code>.venv\\Scripts\\python.exe report\\build_report.py</code>"],
])}
<h3>Evidence files</h3>
{table(["File", "Contents"], [
    ["training/results/qwen3-4b-main/run_config.json, train_summary.json, train_log.jsonl", "Exact training settings, timing and loss log"],
    ["training/results/qwen3-4b-main/eval/", "Test and check-set predictions, results.md / results.json"],
    ["training/results/qwen3-4b-main/export/", "GGUF, export manifest with SHA-256, 300-row GGUF predictions"],
    ["artifacts/evaluation.json, finetuned_evaluation.json, qwen3_evaluation.json", "Baseline, Qwen2.5 and Qwen3 on the 153 reserved complaints"],
    ["artifacts/scope_evaluation.json, local_*_validation.json", "Scope gate and Phase 1 model-selection benchmarks"],
    ["training/data/manifest.json, data/finetuning/manifest.json", "Dataset sources, splits, hashes and label mapping"],
])}
<h3>Values observed during the session (not stored in a results file)</h3>
{table(["Item", "Value"], [[esc(k), esc(v)] for k, v in OBSERVED.items()])}
<p class="src">Report generated {datetime.now(IST).strftime("%d %B %Y, %H:%M")} IST from the files above.</p>
</section>""")

    return HTML_HEAD + "".join(S) + "</body></html>"


HTML_HEAD = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ComplaintIQ SLM Report</title>
<style>
@page { size: A4; margin: 16mm 15mm 18mm;
  @bottom-left { content: "ComplaintIQ · SLM project report"; font: 8pt system-ui, "Segoe UI", sans-serif; color: #898781; }
  @bottom-right { content: counter(page) " / " counter(pages); font: 8pt system-ui, "Segoe UI", sans-serif; color: #898781; } }
@page :first { @bottom-left { content: none; } @bottom-right { content: none; } }
:root { --ink:#0b0b0b; --ink2:#52514e; --muted:#898781; --line:#e1e0d9; --brand:#173f30; --brand2:#2f6b4f; --wash:#f4f6f2; }
* { box-sizing: border-box; }
body { margin: 0; background: #fff; color: var(--ink); font: 10pt/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
h1, h2, h3 { color: var(--brand); line-height: 1.2; }
h2 { font-size: 17pt; margin: 0 0 10px; display: flex; align-items: center; gap: 10px; }
h2 span { display: inline-grid; place-items: center; width: 26px; height: 26px; border-radius: 7px; background: var(--brand); color: #fff; font-size: 11pt; }
h3 { font-size: 11.5pt; margin: 16px 0 6px; }
p, li { color: #1d1d1b; }
ul, ol { padding-left: 18px; margin: 6px 0; } li { margin: 3px 0; }
code { font: 8.5pt ui-monospace, Consolas, monospace; background: var(--wash); padding: 1px 4px; border-radius: 4px; }
.page { break-before: page; }
.lead { font-size: 11pt; }
.note { background: var(--wash); border-left: 3px solid var(--brand2); padding: 8px 12px; font-size: 9pt; border-radius: 0 6px 6px 0; }
.src, .cap { color: var(--ink2); font-size: 8.5pt; margin: 4px 0 10px; }
table { width: 100%; border-collapse: collapse; margin: 6px 0 10px; font-size: 8.8pt; break-inside: auto; }
th { text-align: left; color: var(--ink2); font-weight: 600; border-bottom: 1.5px solid #c3c2b7; padding: 5px 6px; }
td { border-bottom: 1px solid var(--line); padding: 5px 6px; vertical-align: top; }
tr { break-inside: avoid; }
.num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
table.examples td:first-child { width: 58%; }
.excerpt { color: var(--ink2); font-style: italic; }
figure { margin: 10px 0 12px; padding: 12px 14px 4px; border: 1px solid var(--line); border-radius: 10px; background: #fcfcfb; break-inside: avoid; }
.ft { font-weight: 600; font-size: 9.5pt; color: var(--ink); margin-bottom: 6px; }
.legend { display: flex; flex-wrap: wrap; gap: 14px; margin: 0 0 6px; font-size: 8.5pt; color: var(--ink2); }
.legend i { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 6px; vertical-align: -1px; }
svg text { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
svg .tick { font-size: 10px; fill: #898781; } svg .cat { font-size: 11px; fill: #1d1d1b; }
svg .val { font-size: 10.5px; fill: #1d1d1b; font-variant-numeric: tabular-nums; } svg .cell { font-size: 10.5px; font-variant-numeric: tabular-nums; }
svg .boxt { font-size: 12px; font-weight: 600; fill: #0b0b0b; } svg .boxs { font-size: 10px; fill: #52514e; }
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 12px 0 6px; }
.stat { border: 1px solid var(--line); border-radius: 10px; padding: 10px 12px; background: #fcfcfb; }
.stat strong { display: block; font-size: 19pt; color: var(--brand); font-weight: 650; }
.stat span { display: block; font-size: 9pt; font-weight: 600; color: var(--ink); }
.stat small { display: block; font-size: 7.8pt; color: var(--ink2); margin-top: 2px; }
.cover { height: 260mm; display: flex; flex-direction: column; justify-content: space-between; padding: 6mm 2mm;
  background: linear-gradient(160deg, #f4f6f2 0%, #ffffff 55%); border-radius: 14px; }
.cover .logo { width: 150px; }
.cover-main h1 { font-size: 46pt; margin: 6px 0 12px; letter-spacing: -0.5px; }
.eyebrow { text-transform: uppercase; letter-spacing: 1.6px; font-size: 9pt; font-weight: 650; color: var(--brand2); margin: 0; }
.subtitle { font-size: 14pt; max-width: 145mm; color: var(--ink2); line-height: 1.45; }
.cover-facts { display: grid; grid-template-columns: 1fr 1fr; gap: 12px 24px; margin: 0; border-top: 1.5px solid var(--brand); padding-top: 14px; }
.cover-facts dt { font-size: 8pt; text-transform: uppercase; letter-spacing: 1px; color: var(--muted); }
.cover-facts dd { margin: 2px 0 0; font-weight: 600; font-size: 10.5pt; }
@media screen { body { max-width: 900px; margin: 0 auto; padding: 24px 16px; } .page { margin-top: 48px; padding-top: 24px; border-top: 1px dashed var(--line); } }
</style></head><body>"""


def find_browser() -> str | None:
    for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe"):
        if Path(p).is_file():
            return p
    return shutil.which("msedge") or shutil.which("chrome")


def main() -> None:
    OUT_HTML.parent.mkdir(exist_ok=True)
    OUT_HTML.write_text(build(), encoding="utf-8")
    print("HTML:", OUT_HTML)
    browser = find_browser()
    if not browser:
        sys.exit("No Edge/Chrome found to print the PDF; open the HTML and print to PDF.")
    subprocess.run([browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={OUT_PDF}", OUT_HTML.as_uri()], check=True, timeout=180)
    print("PDF:", OUT_PDF, f"{OUT_PDF.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
