# ComplaintIQ implementation status

Updated October 2, 2026. This document separates verified implementation from work still pending.

## Completed and measured

- Local Python complaint workflow: input validation, product/issue classification, LIME product explanation, rule-based priority and department routing, suggested next action, extractive preview, and SQLite complaint history.
- Custom React/TypeScript frontend and FastAPI: operations overview, complaint analysis, searchable/filterable cases, accessible case detail drawer, CSV batch processing/export, and model evidence. The original Streamlit interface remains available as a legacy view.
- Verified production frontend build, strict TypeScript, eight frontend tests, and 55 Python tests. Python coverage across the application and scripts is 85%; Ruff and mypy pass. Browser verification covers saved analysis, queue search, drawer keyboard close, evidence, batch upload, and responsive layouts.
- Real public CFPB historical narratives: 990 unique normalized texts across three product families and nine product/issue classes. Training/validation/test counts are 693/144/153.
- Evaluation artifact identifies the exact training CSV hash (`tfidf-logreg-c304614d53`) and 153 held-out records. Product accuracy **88.24%**, product macro-F1 **89.70%**, issue accuracy **55.56%**, issue macro-F1 **54.57%**, joint product/issue accuracy **55.56%**. Five of 153 records received a review/abstention label; zero inference errors were recorded.
- Actual Q4_K_M Qwen2.5-1.5B-Instruct and Qwen3.5-0.8B checkpoints completed paired 27-complaint local validation runs on the 8 GB M1 alongside the running baseline app, without observed out-of-memory failures. Verified pair-schema joint accuracies were **48.15%** and **22.22%**, respectively; median inference times were **944 ms** and **646 ms**. Qwen2.5-1.5B is selected as the later fine-tuning candidate. The same-sample baseline scored **55.56%** joint accuracy. Full protocol, raw runs and memory limitations are in `docs/LOCAL_MODEL_COMPARISON.md`.
- Optional supplied local GGUF integration is implemented in the Python service. The new application API currently remains baseline-only; the benchmark server is separate. Runtime verification is limited to the measured short-context, one-request-at-a-time workload.
- Prepared Colab/Kaggle QLoRA notebook and training script include smoke testing, persistent checkpoints, held-out original/adapter comparison, and GGUF export instructions.

## Deferred

- Adapting the prepared training workflow to the selected Qwen2.5-1.5B model and running GPU fine-tuning.
- Measuring original versus fine-tuned Qwen classification quality.
- Exporting and testing the actual fine-tuned checkpoint on the 8 GB M1 MacBook, then evaluating the final configuration on the untouched test split.
- Connecting the verified SLM configuration to the new API, then recording and rehearsing the final demo.
- Production service hardening such as authentication, multi-user isolation, hosting and operational monitoring is outside this local assignment demo.

The application currently demonstrates a trained TF-IDF/logistic-regression classifier; separate local benchmarks demonstrate original SLM checkpoints. It must not be presented as a fine-tuned SLM until an actual training run and evaluation are completed. Product accuracy and joint product/issue accuracy are distinct results.

## Dataset and metric limits

The sample comes from the official CFPB December 2011–April 2018 narrative archive, retrieved September 30, 2026. It is balanced and historical; it does not establish contemporary workload or production performance. Exact whitespace/case-normalized narrative duplicates are removed before splitting; near duplicates and recurring templates are not detected.

Macro precision/recall/F1 are averaged across ground-truth classes. Abstentions reduce recall and accuracy; the confusion matrix includes their separate column. Priority and suggested actions are documented demonstration rules, with no trained CFPB severity labels. Summaries are extractive previews.

Evidence: `data/manifest.json`, `artifacts/evaluation.json`, `notebooks/README.md`. Rerun baseline evaluation with `python scripts/evaluate.py`; keep the SLM evaluation as a separate artifact.
