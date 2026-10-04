# Local pilot verification

Verified October 4, 2026 on the local M1 Mac. This supplements the historical October 3 frontend verification; it does not certify unattended production use.

## Automated checks

- Python: 72 passing tests, including migration preservation, revision conflicts, review/lifecycle validation, queue crash recovery, idempotency, cancellation, failed-row retry, model failure, localhost protections and backup restoration.
- Frontend: 19 passing tests, including URL filters/exports, retained correction drafts after conflicts and note updates, resolution requirements, stable submission keys, job deep links, offline case access and single-column CSV parsing.
- Ruff, mypy, strict TypeScript and production Vite build pass.
- Restart recovery is tested by simulating an interrupted running row and starting a new worker. Cancellation/retry/error paths use controlled fake inference to make failures repeatable.

## Actual model and browser walkthrough

Chromium completed a real interactive analysis with the supplied GGUF, saved case `CQ-412756A453`, confirmed a priority correction with a reason, added a note and resolved the case. Native Safari reopened that case with a reason. The original Low priority remained preserved beside the reviewed Medium priority. Actions are attributed to Local operator.

A two-row CSV import (`JOB-9022CE9812C4`) completed after refreshing the page, creating `CQ-6A7EDDEC1A` and `CQ-EBD3905BFC`. Invalid CSV headers display validation errors. A single-column CSV parser problem found during this walkthrough was fixed and covered by a regression test.

Chromium downloaded a filtered case CSV containing exactly the intended confirmed verification case. Safari downloaded `complaintiq-reviewed.csv`, containing one explicitly confirmed supported label record. Backend tests verify exclusion of outside-scope labels.

Safari's Create backup now control created a manual backup. Restoring it into a separate temporary database preserved all rows exactly: 64 complaints, 64 current case records, 4 events, 2 jobs and 3 job rows. The live database was not replaced. The launcher was stopped and restarted successfully, and the final app reported ready on localhost.

A separate temporary workspace was configured with an unavailable model endpoint. Chromium submitted a complaint and displayed a sanitized row error with Retry failed rows. Safari opened the persisted failed job and retried it; both browsers could still read a saved case while the engine was unavailable. This test did not alter the live workspace.

## Desktop presentation

- Chromium screenshots inspected at 1440×900 (cases/detail/imports/empty state) and 1280×800 (Model & System).
- Native Safari exercised case detail/reopen, system diagnostics, manual backup and reviewed-label export.
- Keyboard Tab focus was visible; queue empty states and import validation states were inspected.
- At 1280×800, document width did not exceed the viewport. Browser resource inspection showed no external resource URLs and no browser errors on the checked production page.
- The UI uses system fonts and a self-only resource policy. No cloud dependencies were added. Mobile-specific work is excluded.

## Scope of evidence

Model accuracy was not changed or remeasured by this workflow upgrade. The visible evaluation remains the reserved 153-case result. Mocked automated failures complement the real-model browser walkthrough; every failure combination was not manually exercised in both browsers. Verification created three identifiable test cases in the local workspace and retained them to preserve their history.
