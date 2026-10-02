# ComplaintIQ implementation status

Updated October 2, 2026. This document separates verified implementation from work still pending.

## Completed and measured

- Local Python complaint workflow: input validation, product/issue classification, LIME product explanation, rule-based priority and department routing, suggested next action, extractive preview, and SQLite complaint history.
- Custom React/TypeScript frontend and FastAPI: operations overview, complaint analysis, searchable/filterable cases, accessible case detail drawer, CSV batch processing/export, and model evidence. The original Streamlit interface remains available as a legacy view.
- Verified production frontend build, strict TypeScript, eight frontend tests, and 43 Python tests. Browser verification covers saved analysis, queue search, drawer keyboard close, evidence, batch upload, and responsive layouts.
- Real public CFPB historical narratives: 990 unique normalized texts across three product families and nine product/issue classes. Training/validation/test counts are 693/144/153.
- Evaluation artifact identifies the exact training CSV hash (`tfidf-logreg-c304614d53`) and 153 held-out records. Product accuracy **88.24%**, product macro-F1 **89.70%**, issue accuracy **55.56%**, issue macro-F1 **54.57%**, joint product/issue accuracy **55.56%**. Five of 153 records received a review/abstention label; zero inference errors were recorded.
- Optional supplied local GGUF integration is implemented. Its runtime, memory use and quality have not been verified with real model weights.
- Prepared Colab/Kaggle QLoRA notebook and training script include smoke testing, persistent checkpoints, held-out original/adapter comparison, and GGUF export instructions.

## Deferred

- Running any GPU fine-tuning or downloading model weights.
- Measuring original versus fine-tuned Qwen classification quality.
- Testing an actual SLM checkpoint on the 8 GB M1 MacBook.
- Connecting the SLM to the new API after its local runtime is verified, then recording and rehearsing the final demo.
- Production service hardening such as authentication, multi-user isolation, hosting and operational monitoring is outside this local assignment demo.

The project currently demonstrates a trained TF-IDF/logistic-regression classifier. It must not be presented as a fine-tuned SLM until an actual training run and evaluation are completed. Product accuracy and joint product/issue accuracy are distinct results.

## Dataset and metric limits

The sample comes from the official CFPB December 2011–April 2018 narrative archive, retrieved September 30, 2026. It is balanced and historical; it does not establish contemporary workload or production performance. Exact whitespace/case-normalized narrative duplicates are removed before splitting; near duplicates and recurring templates are not detected.

Macro precision/recall/F1 are averaged across ground-truth classes. Abstentions reduce recall and accuracy; the confusion matrix includes their separate column. Priority and suggested actions are documented demonstration rules, with no trained CFPB severity labels. Summaries are extractive previews.

Evidence: `data/manifest.json`, `artifacts/evaluation.json`, `notebooks/README.md`. Rerun baseline evaluation with `python scripts/evaluate.py`; keep the SLM evaluation as a separate artifact.
