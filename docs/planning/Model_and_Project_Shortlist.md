# ComplaintIQ: model and reusable project shortlist

> **Historical planning note (September 30, 2026).** Qwen3-4B was the first benchmark candidate. Local measurement on the 8 GB M1 later selected **Qwen2.5-1.5B-Instruct**, which is the fine-tuned model in use; see `docs/LOCAL_MODEL_COMPARISON.md` and `docs/FINETUNED_MODEL.md`.

Research date: September 30, 2026. Model cards, repository READMEs, license files, and selected source files were inspected. No candidate application was installed or run; performance and setup claims below remain unverified locally.

## Recommended decision

Use Qwen3-4B-Instruct-2507 as the first model to benchmark. Adapt MohammedHssan11/complaint-routing-intelligence as the Streamlit application foundation. Keep its traditional classifier as a clearly labeled baseline and add the SLM as a separate inference backend. Use selected ideas from mukundjaiswal/financial-complaint-triage for output parsing and evaluation.

This changes the earlier Next.js/FastAPI plan: start with one Streamlit application to reduce implementation effort. Add a separate API only if the assignment requires it. Actual assignment requirements determine whether prompting is enough or fine-tuning is mandatory.

## Model candidates

| Model | Why consider it | Decision |
|---|---|---|
| [Qwen3-4B-Instruct-2507](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507) | 4B, text-only, non-thinking instruction model, Apache-2.0 | Recommended first benchmark; avoids lengthy thinking output |
| [Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B) | Newer 4B language model with vision encoder and hybrid architecture; Apache-2.0 | Challenger if setup, text-only training, and export smoke tests pass |
| [Phi-4-mini-instruct](https://huggingface.co/microsoft/Phi-4-mini-instruct) | 3.8B text model, MIT | Alternative benchmark candidate |
| [Qwen3.5-2B](https://huggingface.co/Qwen/Qwen3.5-2B) | Smaller candidate from the newer family | Consider if 4B inference is too slow or memory constrained; verify the entire runtime/export path |
| [Gemma-3-4b-it](https://huggingface.co/google/gemma-3-4b-it) | Roughly 4B multimodal model; gated, Gemma terms | Lower priority for this text-only assignment |

These are candidate upgrades, not demonstrated complaint-accuracy improvements. Select using the same 100–200 labeled complaint screening set, then use a separate held-out test set for final reporting.

[Qwen3-4B-Instruct-2507 Q4_K_M weights](https://huggingface.co/mradermacher/Qwen3-4B-Instruct-2507-GGUF) are listed at approximately 2.6 GB. That is file size, not total RAM consumption. The MacBook's OS, context cache, runtime buffers, and UI need additional memory. Start at 2,048 context tokens, one request at a time, and short output. Measure actual memory, schema success, and latency before choosing the model. Do not use the advertised 256K context on this laptop.

Use cloud QLoRA for fine-tuning. A 16 GB NVIDIA GPU is a reasonable initial target with short sequences and small batches; fitting and training time depend on the actual setup. Use a supported training notebook from [Unsloth's notebook collection](https://unsloth.ai/docs/get-started/unsloth-notebooks), first with a tiny dataset. Export and test locally before the full run. Community GGUF files represent the original model, not our future fine-tuned adapter.

## Project candidates

### 1. Recommended application foundation

[MohammedHssan11/complaint-routing-intelligence](https://github.com/MohammedHssan11/complaint-routing-intelligence)

Verified [MIT license](https://github.com/MohammedHssan11/complaint-routing-intelligence/blob/main/LICENSE). README describes two Streamlit applications, complaint classification, nested issues, rules for priority, department routing, batch CSV processing, and analytics.

Source inspected: `src/classifier.py`, `app.py`, and `requirements.txt`. The classifier uses TF-IDF and saved scikit-learn models; it is not an SLM. Source returns a default checking/savings category when its model is missing, and a fixed issue confidence in one fallback. Those behaviors must become explicit unavailable/review states. The UI triggers analysis when text is present, so inference must be restricted to deliberate submission before adding a slower SLM. Linear-model token attribution cannot be presented as an explanation of the new SLM.

Work to adapt:

1. Establish a working baseline installation and verify required data/model artifacts.
2. Add a cached local SLM backend and model selector.
3. Validate JSON labels and align them with the app's taxonomy.
4. Retain priority/routing as labeled demo rules and action templates.
5. Remove unsupported legal determinations, risk percentages, confidence percentages, and inherited benchmark claims from our demo.
6. Add SQLite history, our own measured evaluation, model/version labels, and ComplaintIQ branding.
7. Preserve the upstream license and document which parts we changed.

This is a close foundation, but not a turnkey fine-tuned SLM assignment.

### 2. Useful local SLM component

[mukundjaiswal/financial-complaint-triage](https://github.com/mukundjaiswal/financial-complaint-triage)

Verified [MIT license](https://github.com/mukundjaiswal/financial-complaint-triage/blob/main/LICENSE). It provides local quantized-model classification, summarization, normalization, CLI, and evaluation structure. It explicitly uses no fine-tuning and has no complete dashboard or committed evaluation dataset.

Inspected its GGUF adapter and package dependencies. Its adapter uses raw completion and does not explicitly enable Metal offload; adapt the chat template, generation handling, and runtime settings for our chosen model and Apple Silicon. It also depends on the author's separate evaluation harness. Reusing selected components may be simpler than combining both applications wholesale.

Do not inherit its reported scores: the README says its evaluation sets contain only 30 and 50 examples.

### 3. Analytics alternative

[S-Harish-Dev/Financial_Complaint_Risk_Intelligence](https://github.com/S-Harish-Dev/Financial_Complaint_Risk_Intelligence)

Verified [MIT license](https://github.com/S-Harish-Dev/Financial_Complaint_Risk_Intelligence/blob/main/LICENSE). README describes Streamlit, traditional classification, historical similarity matching, and complaint trends. Useful if the assignment emphasizes analytics. It is not an SLM application as supplied. Its benchmark and calibration claims have not been independently verified.

### Candidates not selected

- [Joshua128/Complain-Analyzer](https://github.com/Joshua128/Complain-Analyzer): relevant DistilBERT classifier, batch dashboard, and training notebooks. A root `LICENSE` fetch returned 404, so reuse permission was not established in this review.
- [princeixr/Multi-Agent-Financial-Complaint-System](https://github.com/princeixr/Multi-Agent-Financial-Complaint-System): broad UI and workflows, but requires provider APIs, PostgreSQL/pgvector, and OCR components. README explicitly says no license file is included. Too much setup for this assignment.
- [code88morning-cmd/financial-complaint-llm-assistant](https://github.com/code88morning-cmd/financial-complaint-llm-assistant): FastAPI with hosted API integration, Korean-oriented examples, and rule-based demo mode. Does not directly meet the local trained-SLM objective.

## Minimum-effort execution path

1. Benchmark Qwen3-4B-Instruct-2507 locally and get the reusable Streamlit app working.
2. Integrate prompted SLM predictions and explicitly label this as an unfine-tuned checkpoint.
3. If fine-tuning is required, train on Colab/Kaggle, export, and replace the model artifact.
4. Add polished result cards, complaint history, actual analytics, and a comparison screen.
5. Prepare a short demo video and README showing upstream credits and our contributions.

Estimated effort: 5–8 focused days for a prompted SLM demo if the foundation runs cleanly; approximately 8–12 for fine-tuning and evaluation. These estimates depend on skills, model/export compatibility, and free GPU availability.

Local-only use still needs permission to modify code. The selected MIT repositories grant that permission with notice-preservation conditions. Present the result as an adapted project and describe the SLM integration and evaluation that we added. Check the company's assignment rules before assuming reuse satisfies its originality requirements.
