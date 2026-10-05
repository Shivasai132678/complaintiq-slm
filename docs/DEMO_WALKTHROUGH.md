# Company walkthrough: ComplaintIQ local pilot

Start `sh run_pilot.sh` and open http://127.0.0.1:8501. Model & System should show the fine-tuned local engine connected. Keep the launcher terminal open.

## Five-minute presentation

1. **The problem — 30 seconds.** “A complaint classification is only the beginning. An operator needs to review it, route it, track what changed, and close the case.”
2. **Analyze — 45 seconds.** Submit the illustrative input below. Show the persistent processing state and open the saved case. Explain the 2,000-character model processing limit and the unreviewed state.
3. **Review — 90 seconds.** Compare the original model classification and policy priority with reviewer decisions. Correct or confirm the labels, select a department, enter a reason for changes and save. Add a note. Resolve with a resolution note, then reopen with a reason to show the activity history. Original predictions remain unchanged.
4. **Operations — 45 seconds.** Open Cases, search/filter the queue and export the filtered results. Show Overview's current lifecycle counts. These are workspace statistics, not accuracy measurements.
5. **Reliability — 30 seconds.** Show Imports, a completed batch and row-level results. Explain serial processing, refresh/restart recovery, failed-row retry and duplicate-submission protection. Create a database backup in Model & System.
6. **Evidence and limits — 60 seconds.** Show the measured 153-case evaluation: 88.89% product accuracy and 54.25% joint accuracy. Explain why human review is essential, that priority/routing use rules, and that supported scope is three product families and nine product/issue pairs. Export reviewed labels; exporting never starts retraining.

## Suggested input

The Analyze page has one-click examples (Late fee, Duplicate charge, Credit report error, Deposit hold, Out of scope). Use one of them during the live demo so there is no typing. The "Out of scope" example shows the scope gate: the case goes straight to review with the reason, and the model is not run.


```text
My credit card statement includes a duplicate merchant charge. I disputed the transaction and the bank has not reversed the extra payment.
```

This is an authored demonstration input, not a promised prediction. For a batch, use a CSV with a `text` header, up to 100 non-empty narratives and 2 MB total. Each narrative may contain at most 6,000 characters.

## What makes this useful

The value is a repeatable local review workflow: consistent labels, persistent cases, operator corrections, routing, history and recovery. It is more convenient for repeated complaint operations than manually copying prompts and responses between a general chat tool and a spreadsheet. All inference and case processing run on this Mac after setup.

Describe it as a polished single-operator pilot. Do not claim that it outperforms general-purpose models, is compliant with financial regulations, or is ready for unattended decisions. The baseline joint accuracy was 55.56%; the current fine-tuned model does not establish an overall test-accuracy improvement.

## Supporting material

- `docs/LOCAL_PILOT.md`: startup, interfaces, processing and restore commands.
- `docs/PILOT_VERIFICATION.md`: verification evidence and limits.
- `docs/FINETUNED_MODEL.md`: model provenance and measured evaluation.

Future work can improve issue classification, evaluate the remaining 747 reserved test cases, and expand supported product coverage under a separate evaluation protocol. No additional training is part of this delivery.
