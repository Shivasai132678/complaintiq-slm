# ComplaintIQ

A local financial complaint triage assignment with a custom React/TypeScript interface and FastAPI backend: complaint classification, explained priority rules, suggested department/actions, saved cases, CSV processing, analytics, and evaluation evidence.

## Current model status

Training and model setup are deferred at the user's request. The completed application uses the baseline until that separate phase starts.

The default backend is a real **TF-IDF + Logistic Regression baseline**, trained at startup from bundled public CFPB narratives. It requires no GPU or hosted API. The app explicitly labels this backend.

The selected fine-tuning candidate is **Qwen2.5-1.5B-Instruct**, based on actual local validation runs. See [docs/LOCAL_MODEL_COMPARISON.md](docs/LOCAL_MODEL_COMPARISON.md). The optional local **GGUF** backend uses a user-supplied checkpoint. A cloud QLoRA training workflow is included separately. A supplied original checkpoint is not a fine-tuned model. No fine-tuning completion or SLM accuracy is claimed unless an actual trained checkpoint and evaluation report are produced. Model weights are not bundled or automatically downloaded, respecting the 8 GB M1/storage constraints.

## Run locally

Use Python 3.12 and Node.js 22.12+ (verified with 22.22). This workspace already has `.venv` installed. The frontend's production build is served by the local Python API; a separate frontend server is not required for the demo.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cd frontend
npm ci
npm run build
cd ..
sh run_demo.sh
```

Open http://127.0.0.1:8501. The server binds only to loopback. Complaint text and analysis history remain in `data/complaintiq.sqlite3`; this database is excluded from Git. Raw public CFPB complaint narratives are included in the small training/evaluation CSVs with source provenance. The earlier Streamlit interface remains available with `sh run_streamlit.sh` on port 8503.

To populate an empty dashboard with clearly identified public demo complaints:

```sh
.venv/bin/python -m scripts.seed_demo
```

This command uses held-out public records for demonstration, not for retraining. It skips a database that already contains complaints.

## Model behavior

- Product and issue: either the trained baseline or the selected local SLM.
- Priority and routing: configurable demonstration rules with matched reasons. These are not legal assessments or trained CFPB severity labels.
- Suggested action: category-based templates for human review.
- Summary: a clearly labeled extractive preview, not a generated resolution.
- Explanation: baseline LIME product attribution; optional SLM LIME is expensive and disabled by default.
- Unsupported labels, missing weights, or invalid model outputs produce an explicit error/review state. The app never silently substitutes the baseline for an SLM request.
- No invented confidence or regulatory-risk percentages.

Local SLM inference requires a compatible `llama-cpp-python` install and a valid GGUF file. The legacy Streamlit interface supports setting a local model path in its sidebar. The new web API intentionally exposes only the verified baseline while model setup is deferred. Use short context and one request at a time on the M1; the selected 1.5B GGUF was measured through a standalone llama.cpp server alongside the app. The in-process Python SLM integration and fine-tuned checkpoint remain to be verified. Model selection and output schema are version-controlled in `complaintiq/models.py`.

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

## Attribution and scope

Adapted from the MIT-licensed [complaint-routing-intelligence](https://github.com/MohammedHssan11/complaint-routing-intelligence) project. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Upstream pickle files and claimed benchmark figures are not used. Our own source data, tests, evaluations, and changes are documented here.

This is an assignment prototype. Public data samples and a small evaluation split establish reproducibility; they do not prove production suitability. The company assignment's originality and fine-tuning requirements still govern submission.

See [Model_and_Project_Shortlist.md](Model_and_Project_Shortlist.md) for the model/reuse decision and [ComplaintIQ_Assignment_Plan.md](ComplaintIQ_Assignment_Plan.md) for the original broader plan.

Use [docs/DEMO_WALKTHROUGH.md](docs/DEMO_WALKTHROUGH.md) for a five-minute company demonstration and presentation outline, and [docs/STATUS.md](docs/STATUS.md) for verified progress. The current implementation uses a custom React frontend, FastAPI, and SQLite, with model training deferred. The backend is reusable; the Streamlit prototype remains as a legacy interface.

## Frontend development

Start the API on port 8502 with `.venv/bin/python -m uvicorn complaintiq.api:app --host 127.0.0.1 --port 8502`. In another terminal, run `npm run dev` in `frontend/`; Vite forwards `/api` requests to that port. No paid API, hosted service, or cloud deployment is needed.
