# ComplaintIQ

A local financial complaint review pilot with React/TypeScript, FastAPI and a fine-tuned model: classification, human corrections, case lifecycle, notes/history, durable CSV processing, backups and evaluation evidence.

See [the local pilot guide](docs/LOCAL_PILOT.md) for review workflows, API contracts, startup and recovery.

## Current model status

The demo now runs the supplied **fine-tuned Qwen2.5-1.5B-Instruct Q4_K_M GGUF** through a local llama.cpp Metal server on the M1 Mac. The supplied model was exported from Unsloth checkpoint-563 after cloud QLoRA training. We verified its local file hash and measured its predictions; the cloud training configuration is based on the supplied export/session, rather than independently reproduced locally.

On 153 reserved test complaints, product accuracy is **88.89%**, joint product/issue accuracy **54.25%**, and mean inference latency **953 ms**. The baseline scored **88.24%** product and **55.56%** joint accuracy on the same split. Fine-tuning does not establish a joint-accuracy improvement here. See [docs/FINETUNED_MODEL.md](docs/FINETUNED_MODEL.md) for measured evidence and limitations.

## Windows PC (training + app)

To train the new Qwen3-4B model and run the whole app on a fresh Windows 11 PC with an NVIDIA GPU, copy the project with `sh pc_kit/mac_prep/make_pc_bundle.sh <destination>` and follow [pc_kit/README.md](pc_kit/README.md). Everything is installed offline: on the PC, double-click `RUN_ALL.bat` (setup, training, export, app, in order; `RESUME_ALL.bat` continues after an interruption).

## Run locally

Use Python 3.12 and Node.js 22.12+ (verified with 22.22). This workspace already has `.venv` installed. The frontend's production build is served by the local Python API; a separate frontend server is not required for the demo.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cd frontend
npm ci
npm run build
cd ..
# Start both services with readiness checks
sh run_pilot.sh
```

Open http://127.0.0.1:8501. The server binds only to loopback. Complaint text and analysis history remain in `data/complaintiq.sqlite3`; this database is excluded from Git. Raw public CFPB complaint narratives are included in the small training/evaluation CSVs with source provenance. The earlier Streamlit interface remains available with `sh run_streamlit.sh` on port 8503.

To populate an empty dashboard with clearly identified public demo complaints:

```sh
.venv/bin/python -m scripts.seed_demo
```

This command uses held-out public records for demonstration, not for retraining. It skips a database that already contains complaints.

## Model behavior

- Product and issue: either the trained baseline or the selected local SLM. A scope gate runs first and sends unrelated or other-product complaints to review without classifying them (see `artifacts/scope_evaluation.json`).
- Priority and routing: configurable demonstration rules with matched reasons. These are not legal assessments or trained CFPB severity labels.
- Suggested action: category-based templates for human review.
- Summary: a clearly labeled extractive preview, not a generated resolution.
- Explanation: baseline LIME product attribution; optional SLM LIME is expensive and disabled by default.
- Unsupported labels, missing weights, or invalid model outputs produce an explicit error/review state. The app never silently substitutes the baseline for an SLM request.
- No invented confidence or regulatory-risk percentages.

The React/FastAPI demo uses the existing Homebrew `llama-server` through local HTTP; no `llama-cpp-python` installation is needed for this path. Run `sh run_pilot.sh` for a supervised local startup. The two-script startup remains available. The server uses 2,048 context tokens and processes one request at a time; classification reads the first 2,000 normalized characters. Full complaint text is retained in the local history. Strict decoding and independent validation enforce the allowed product/issue pairs. SLM LIME is disabled to keep inference fast; priority and routing remain explicit rules. Select the baseline explicitly with `COMPLAINTIQ_BACKEND=baseline sh run_demo.sh`. Inference failures never silently switch engines.

## Verification

```sh
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest --cov=complaintiq --cov-report=term-missing
.venv/bin/python -m ruff check app.py complaintiq scripts tests
.venv/bin/python -m mypy app.py complaintiq scripts
cd frontend
npm test
npm run build
```

`requirements-lock.txt` records the complete verified local dependency environment. GPU training dependencies are separate from this small local environment.

The larger, separately prepared SLM dataset lives in `data/finetuning/`. See [docs/FINETUNING_DATASET.md](docs/FINETUNING_DATASET.md) for provenance, split protection and Unsloth upload instructions. The original baseline data remains unchanged.

## Attribution and scope

Adapted from the MIT-licensed [complaint-routing-intelligence](https://github.com/MohammedHssan11/complaint-routing-intelligence) project. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Upstream pickle files and claimed benchmark figures are not used. Our own source data, tests, evaluations, and changes are documented here.

This is a single-operator local pilot, not an unattended or multi-user production service. Public data samples and a small evaluation split establish reproducibility; they do not prove production suitability. The company assignment's originality and fine-tuning requirements still govern submission.

See [Model_and_Project_Shortlist.md](Model_and_Project_Shortlist.md) for the model/reuse decision and [ComplaintIQ_Assignment_Plan.md](ComplaintIQ_Assignment_Plan.md) for the original broader plan.

Use [docs/DEMO_WALKTHROUGH.md](docs/DEMO_WALKTHROUGH.md) for a five-minute company demonstration and presentation outline, and [docs/STATUS.md](docs/STATUS.md) for verified progress. The current implementation uses a custom React frontend, FastAPI, and SQLite, with local fine-tuned SLM inference connected. The backend is reusable; the Streamlit prototype remains as a legacy interface.

## Frontend development

Start a separate development database/API on port 8502 with `COMPLAINTIQ_DB_PATH=/private/tmp/complaintiq-dev.sqlite3 .venv/bin/python -m uvicorn complaintiq.api:app --host 127.0.0.1 --port 8502 --no-access-log`. In another terminal, run `npm run dev` in `frontend/`; Vite forwards `/api` requests to that port. No paid API, hosted service, or cloud deployment is needed.
