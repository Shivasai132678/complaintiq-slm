# ComplaintIQ implementation status

Updated October 4, 2026. This document separates verified implementation from work still pending.

## Local pilot delivered

- Dedicated case pages, URL-backed queues, review corrections, notes, lifecycle transitions and append-only local activity history.
- Versioned migration preserves original cases and predictions; revisions reject stale writes. Confirmed supported labels have a separate export.
- Durable serial processing for analysis and CSV imports (100 rows / 2 MB), cancellation, failed-row retry and restart recovery.
- One launcher, model-independent case browsing, manual/daily backups and an offline validated restore command.
- Ivory/forest-green desktop interface with system fonts, visible keyboard focus and reduced-motion support.
- Current verification: 72 Python tests, 19 frontend tests, Ruff, mypy, strict TypeScript and production build pass. Native Safari and Chromium walkthroughs exercised the actual model and review workflow. See [pilot verification](PILOT_VERIFICATION.md) and [operation guide](LOCAL_PILOT.md).

## Earlier implementation and measured model evidence

- Local Python complaint workflow: input validation, product/issue classification, LIME product explanation, rule-based priority and department routing, suggested next action, extractive preview, and SQLite complaint history.
- Custom React/TypeScript frontend and FastAPI: operations overview, complaint analysis, searchable/filterable cases, accessible case detail drawer, CSV batch processing/export, and model evidence. (The original Streamlit interface was removed on October 9, 2026.)
- Verified production frontend build, strict TypeScript, 11 frontend tests, and 66 Python tests. Ruff and mypy pass. Desktop Safari verification covers real fine-tuned inference, saved analysis, queue search, drawer keyboard close, model evidence, invalid/valid CSV upload, and downloaded batch/evaluation reports. Details are in `docs/FRONTEND_VERIFICATION.md`.
- Real public CFPB historical narratives: 990 unique normalized texts across three product families and nine product/issue classes. Training/validation/test counts are 693/144/153.
- Separately prepared larger SLM dataset: 9,000 training, 900 validation and 900 test examples across the same nine categories, preserving all original split assignments. JSONL chat examples, CSV audit records and a provenance manifest are in `data/finetuning/`. Exact input/ID cross-split overlaps are zero; conservative approximate near-duplicate filtering is documented in `docs/FINETUNING_DATASET.md`. The user completed cloud training and supplied the exported checkpoint; local inference and evaluation are now verified.
- Evaluation artifact identifies the exact training CSV hash (`tfidf-logreg-c304614d53`) and 153 held-out records. Product accuracy **88.24%**, product macro-F1 **89.70%**, issue accuracy **55.56%**, issue macro-F1 **54.57%**, joint product/issue accuracy **55.56%**. Five of 153 records received a review/abstention label; zero inference errors were recorded.
- Actual Q4_K_M Qwen2.5-1.5B-Instruct and Qwen3.5-0.8B checkpoints completed paired 27-complaint local validation runs on the 8 GB M1 alongside the running baseline app, without observed out-of-memory failures. Verified pair-schema joint accuracies were **48.15%** and **22.22%**, respectively; median inference times were **944 ms** and **646 ms**. Qwen2.5-1.5B is selected as the later fine-tuning candidate. The same-sample baseline scored **55.56%** joint accuracy. Full protocol, raw runs and memory limitations are in `docs/LOCAL_MODEL_COMPARISON.md`.
- Optional supplied local GGUF integration is implemented in the Python service. The application API now supports the fine-tuned local llama.cpp server as well as an explicitly selected baseline. Runtime verification is limited to the measured short-context, one-request-at-a-time workload.
- Prepared Colab/Kaggle QLoRA notebook and training script include smoke testing, persistent checkpoints, held-out original/adapter comparison, and GGUF export instructions.

## Fine-tuned model connected

The supplied checkpoint-563 Q4_K_M model is verified on the M1 and connected to React/FastAPI. A 27-case validation smoke test measured 96.30% product accuracy and 74.07% joint accuracy, compared with 48.15% joint accuracy for the original Qwen in the same schema mode. The final 153-case reserved test evaluation measured **88.89% product accuracy**, **54.25% joint accuracy**, and **953 ms mean latency**. The test joint result is slightly below the baseline's 55.56%; do not claim a general improvement from the validation smoke test.

The evaluation is a preserved 153-case subset of the expanded 900-case test split. The remaining 747 cases have not been evaluated. Evidence: `artifacts/finetuned_validation_smoke.json`, `artifacts/finetuned_evaluation.json`, and `docs/FINETUNED_MODEL.md`.

## Scope gate

Unrelated and other-product complaints are routed to review before inference. Held-out results: 94.4% of unrelated and 62.8% of other-product complaints caught; 2.4% of supported complaints sent to review. Evidence: `artifacts/scope_evaluation.json`, `docs/FINETUNED_MODEL.md`.

## Remaining scope

- Rehearse and record the company demo.
- Further training or evaluation of all 900 test cases is optional future work; additional training requires a fresh final evaluation protocol.
- Authentication, multi-user isolation, cloud hosting and unattended operation remain outside this single-operator local pilot.

## Dataset and metric limits

The sample comes from the official CFPB December 2011–April 2018 narrative archive, retrieved September 30, 2026. It is balanced and historical; it does not establish contemporary workload or production performance. Exact whitespace/case-normalized narrative duplicates are removed before splitting; near duplicates and recurring templates are not detected.

Macro precision/recall/F1 are averaged across ground-truth classes. Abstentions reduce recall and accuracy; the confusion matrix includes their separate column. Priority and suggested actions are documented demonstration rules, with no trained CFPB severity labels. Summaries are extractive previews.

Evidence: `data/manifest.json`, `artifacts/evaluation.json`, `notebooks/README.md`. Rerun baseline evaluation with `python scripts/evaluate.py`; keep the SLM evaluation as a separate artifact.
