# ComplaintIQ local pilot

This version supports one local operator on one Mac. It runs the fine-tuned Qwen3-4B GGUF and adds a human review workflow, persistent processing, recovery tools and a new desktop interface.

## Start and stop

After installing the existing Python requirements, llama.cpp and frontend dependencies, build with `cd frontend && npm run build`. From the repository root:

```sh
sh run_pilot.sh
```

Open http://127.0.0.1:8501. Keep the terminal open. Ctrl+C stops only the model/app processes started by this launcher. A compatible pre-existing model server is reused and left running. Port conflicts are reported rather than terminated automatically. The launcher requires the configured GGUF and the production frontend build; it does not download models.

`run_demo.sh` starts the same app with the baseline classifier only (no model server). Use one API process per database; the queue holds an OS file lock. Do not run a second writer against the database during restoration or pilot use. For development, use a separate `COMPLAINTIQ_DB_PATH` and stop its API before restoring that database.

## Review a complaint

1. Analyze a narrative or upload a CSV from Imports. All work runs through one durable queue. The original API input limit remains 6,000 characters; inference uses the first 2,000 normalized characters.
2. Open the case. Read the full narrative and the original model/policy assessment.
3. Confirm or correct the product/issue, priority and department. Corrections require a reason. A changed product suggests a department that the reviewer confirms when saving.
4. Use **Outside supported scope** when the narrative does not belong to the current taxonomy. This is a human decision, not a model confidence score.
5. Add notes, start review, and resolve with a resolution note after confirming the classification. Reopening requires a reason.
6. Use case history to inspect changes. Predictions and narratives are retained unchanged; the UI never presents reviewer corrections as the original model output.

Every new or migrated case starts unreviewed. Legacy `Needs review` becomes a review flag with lifecycle state `Queued`. Migration does not manufacture historical events. A revision check prevents two browser tabs from overwriting each other. After a conflict, load the latest revision and inspect history before resubmitting the retained draft.

## Imports and failure recovery

CSV files require a `text` column, at most 100 rows and 2 MB. Blank narratives, narratives over 6,000 characters and malformed CSVs are rejected before processing. Successful rows create individual cases. Closing or refreshing the browser does not cancel work.

The queue persists each row. One row is processed at a time; saving the case and completing the row occur in one database transaction. Interrupted running rows return to pending at application startup. Reprocessing an interrupted inference can spend compute again, but it cannot duplicate a committed case. Submission keys prevent accidental repeated submissions of the same request.

Cancel stops pending rows; an active row can finish. Retry requeues failed rows only, retaining completed cases. A model error never switches to the baseline. Saved cases and review controls remain available when the model is down. Processing history shows the latest 50 jobs; older jobs remain accessible by their saved job URL.

## Back up and restore

The database is `data/complaintiq.sqlite3`. Its sibling `backups/` directory contains a backup before legacy schema migration, daily startup backups (seven automatic backups retained), and manual backups created from Model & System. Manual and migration backups are not automatically removed. Logs, databases and backups are excluded from Git.

To restore, stop the application and any legacy process writing the database, then run:

```sh
.venv/bin/python scripts/restore_backup.py 'data/backups/CHOOSE-A-BACKUP.sqlite3'
```

The command validates the source and takes a pre-restore backup of an existing destination. It refuses restoration while the pilot worker owns the database lock. To verify a backup without touching the live database:

```sh
.venv/bin/python scripts/restore_backup.py 'data/backups/CHOOSE-A-BACKUP.sqlite3' --database /private/tmp/complaintiq-restore-check.sqlite3
```

Backups contain raw narratives; they are not encrypted by this application. Protect the Mac and backups using the operating system's access controls and disk protection. Review history is attributed to `Local operator`, not a verified individual identity.

## Interfaces

- `GET /api/config`, `/api/cases`, `/api/cases/{id}`, `/api/overview`: configuration and read-only case workflow, independent of model initialization.
- `PATCH /api/cases/{id}/review`: `revision`, `product`, `issue`, `priority`, `department`, `reason`.
- `POST /api/cases/{id}/notes`: `revision`, `reason`; `POST /api/cases/{id}/transition`: `revision`, `status`, `reason`. Stale revisions return 409.
- `GET /api/cases/export`: the same search/filter parameters as the queue. `kind=reviewed` includes only human-confirmed supported product/issue labels. CSV formula-like values are escaped for safe spreadsheet opening; account for this when preparing training data.
- `POST /api/jobs`: `texts`, `request_key`, `source` (`analysis` or `import`). Returns 202 and a job ID. `GET /api/jobs/{id}` returns row progress. POST `/cancel` or `/retry` under the job URL controls it.
- `GET /api/system`, `POST /api/backups`: storage/queue diagnostics and manual backup.
- Existing `/api/complaints`, `/api/batch`, `/api/analytics`, `/api/health`, `/api/evaluation` are retained. Synchronous inference endpoints use the same queue. Legacy list/analytics endpoints describe original prediction records; the new case/overview endpoints describe current reviewer decisions.

All write requests require JSON. Browser writes require the same origin; allowed hosts are loopback and the internal test client. No accounts, network hosting or multi-user permissions are provided. Do not expose either local service publicly.

## Model limits

On the 153 reserved test complaints the Qwen3-4B GGUF scores 90.85% product accuracy and 58.82% joint product/issue accuracy (`artifacts/qwen3_evaluation.json`). The pilot redesign does not improve model accuracy. Three product families and nine label pairs remain supported. Priority/routing are explicit policies. Reviewed exports do not automatically retrain anything and must not contaminate future held-out evaluation sets.
