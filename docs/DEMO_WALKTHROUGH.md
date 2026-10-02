# Company demo walkthrough

## Current scope

The application and data workflow are complete for the baseline demo. Training and model setup are deliberately deferred at the user's request. Say "SLM-ready complaint intelligence prototype" until a real SLM checkpoint is configured and tested.

## Five-minute presentation

1. **Problem (30 seconds):** Financial complaints arrive as unstructured narratives. ComplaintIQ turns them into a reviewable product, issue, priority, and suggested department.
2. **Live analysis (60 seconds):** Open Analyze, choose Unauthorized card charge under Try an example, then select Analyze complaint. Explain which fields come from classification and which come from explicit rules. The extractive preview preserves the original words.
3. **Explainability (30 seconds):** Inspect What influenced the classification in the result panel. LIME token weights explain the baseline's product prediction; they are not confidence percentages.
4. **Queue (45 seconds):** Open Cases, search for the submitted complaint, filter priority, inspect its saved result, and show CSV export.
5. **Analytics (45 seconds):** Open Overview. The seeded public complaints and newly submitted case appear in actual saved prediction counts. Explain product, priority, and routing distributions.
6. **Evidence (45 seconds):** Open Model evidence. Show genuine held-out baseline metrics and the confusion matrix. Issue classification is harder than product classification; do not hide errors or claim SLM improvement before measuring it.
7. **Next step (30 seconds):** The separate cloud notebook prepares QLoRA training. Later, export the checkpoint, verify local inference, connect it to the API, and compare it with this baseline on the same held-out complaints.

## Suggested live input

```text
I found an unauthorized charge on my credit card statement. I notified the card company immediately, but they refused to investigate and charged interest on the disputed amount.
```

Example inputs are authored illustrations, not model outputs. The app analyzes them on submission. The bundled dataset is real, historical CFPB public data, sampled for this assignment.

## Optional batch demo

Upload `data/demo_upload.csv` under Batch upload. The app requires a `text` column, caps processing at 20 rows, saves valid complaints, and identifies row-level errors. Download the processed CSV.

## Presentation checklist

- Start `sh run_demo.sh` and open the local page before presenting.
- The new API uses Baseline until a trained model is verified and integrated.
- Confirm Model evidence displays the committed evaluation report.
- Rehearse the input and queue search; use an unfamiliar input as an additional demonstration.
- Keep the upstream attribution in the README and explain your integration work if asked.
- No internet connection is needed for the installed baseline demo.

## Five-slide outline

1. **ComplaintIQ:** problem, user, and triage workflow.
2. **Architecture:** React/TypeScript → FastAPI → complaint service → baseline → SQLite; optional local SLM runtime prepared for later integration.
3. **Data:** official archived CFPB narratives; 990 selected records, three products, nine issues; disjoint splits and documented limitations.
4. **Evidence:** measured baseline results, confusion matrix, explanations, and known failure cases.
5. **Demo and next step:** live queue/dashboard; deferred cloud fine-tuning and model comparison.
