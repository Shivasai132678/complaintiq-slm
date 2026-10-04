# Desktop demo verification

Verified October 3, 2026 against the production frontend served by FastAPI at http://127.0.0.1:8501, with the supplied checkpoint-563 Qwen2.5-1.5B-Instruct Q4_K_M GGUF running through llama.cpp on Apple M1.

## Changes

- Analysis results identify product and issue as model predictions, with a separate workflow section for priority and routing policies. Complaint previews are labelled narrative excerpts.
- Analyze identifies the active fine-tuned Qwen engine. Model evidence shows one active classification model, its loaded file, format, training sample count and output scope.
- Engine health checks verify availability and loaded model identity. The frontend refreshes status periodically and clears a previous result before a new request, including when that request fails.
- Truncated inputs and cached results are labelled explicitly. Existing cases retain the model that originally classified them.

## Verified desktop flow

Native Safari submitted a checking-account overdraft complaint. The actual local model returned Checking or savings account / Problems caused by my funds being low in 0.89 seconds. Case CQ-419066E85A was saved, found through the query `automated transfer`, and inspected in the detail drawer. Model prediction and workflow policy sections were visually checked; Escape closed the drawer.

An invalid CSV with `wrong_column` displayed the missing `text` column error and disabled processing. A valid two-row CSV showed a preview, then saved both locally classified complaints: CQ-8C302E95C2 (Credit reporting / Incorrect information on your report) and CQ-66AE4D7C42 (Credit card / Billing disputes). The queue grew from 59 to 61 cases.

The batch export was downloaded through Safari and parsed as two CSV rows with the matching product labels. The evaluation download was parsed as JSON and confirmed to contain the measured 153-case report. The evidence page was visually inspected for the active engine, actual GGUF filename, metrics and methodology.

The isolated automation browser was closed. Mobile checks were stopped at the user's request. The application and model server remain running.

## Automated checks and limits

66 Python tests and 11 frontend tests pass. Strict TypeScript and production build pass; Ruff and mypy pass. Tests cover model identity mismatch, unavailable inference, invalid label pairs, context limits, caching, API backend selection, model availability, UI result ownership, and clearing stale results on failure.

Desktop workflow checks establish integration, not universal prediction accuracy. The measured test product accuracy is 88.89% and joint product/issue accuracy is 54.25%. Priority and routing remain configured policies; the model is trained to predict product and issue. Authentication and multi-user hosting are outside this local demo.
