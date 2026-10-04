# Presentation Q&A cheat sheet

Short, honest answers to the questions a reviewer is most likely to ask. Numbers come from `artifacts/` and `docs/FINETUNED_MODEL.md`.

## The model

**Which model did you fine-tune, and how?**
Qwen2.5-1.5B-Instruct, with Unsloth 4-bit QLoRA on a free Colab GPU. Training data: 9,000 real CFPB complaints (1,000 per issue class) in `data/finetuning/training.jsonl`. The run was exported from checkpoint-563 as a Q4_K_M GGUF (about 986 MB) and runs on the Mac through llama.cpp Metal. Workflow: `notebooks/train_qwen25_colab.ipynb`.

**Why a 1.5B model, not something bigger?**
It had to run privately on an 8 GB M1, one request at a time, at about 1 second per complaint. On a local benchmark it beat Qwen3.5-0.8B by 26 points of joint accuracy (48% vs 22%) for about 0.3 s more latency. A 4B model was planned first but doesn't fit comfortably beside the app on 8 GB.

**Why not just call GPT or Claude?**
Complaint narratives contain personal financial data. Everything here runs offline on the laptop: no API cost, no data leaving the device, and a fixed, auditable label set.

## The results

**What accuracy do you get?**
On 153 held-out test complaints: 88.89% product accuracy (macro-F1 88.6%) and 54.25% joint product + issue accuracy. Latency: mean 953 ms, median 860 ms, p95 about 1.5 s. Zero invalid outputs.

**The fine-tuned model doesn't beat the TF-IDF baseline. So why fine-tune?**
- On joint accuracy it's a tie: 54.25% vs 55.56% is 2 complaints out of 153, well inside noise for a sample this size.
- Fine-tuning clearly helped the SLM itself. On the validation sample, joint accuracy went from 48% to 74%, and product accuracy from 78% to 96%.
- The baseline is only a reference point for a narrow 9-class problem. The SLM path is what extends: new labels via instructions and data, schema-validated JSON, room for summaries or extraction later.
- We report the tie instead of hiding it.

**Where does it fail?**
On issue classes that overlap in meaning: "Other" (credit card, 24% recall), "Problem with a credit reporting company's investigation" (29%), and "Incorrect information on your report" (47%). Consumers often pick between these inconsistently in the CFPB data itself, so the labels are noisy. Product-level routing is reliable; issue-level labels need human confirmation, which is why the review workflow exists.

**Why only 153 test cases?**
These are the original reserved test cases, kept frozen from the first day. The expanded split has 900. Running all of them takes about 15 minutes: `.venv/bin/python -m scripts.evaluate_server --test-file data/finetuning/test.csv --output artifacts/finetuned_evaluation_900.json`.

**Any data leakage?**
No IDs or exact normalized inputs are shared across splits. An approximate near-duplicate filter removed 65 candidates. Paraphrase-level leakage can't be fully ruled out (see `docs/FINETUNING_DATASET.md`).

## The product

**Is priority predicted by the model?**
No. Priority, department routing and suggested actions are transparent rules, and each shows the reason it matched. CFPB data has no severity labels, so a learned priority would be invented.

**Can it hallucinate?**
Output is constrained to the nine allowed product/issue pairs and then validated independently. Anything invalid becomes an explicit error or review state, never a silent fallback. Summaries are extractive (real sentences from the complaint), not generated.

**What happens when a reviewer disagrees?**
They correct the labels with a reason. The original prediction is kept unchanged, and every change is written to an append-only activity history. Confirmed labels can be exported as future training data. Exporting never retrains automatically.

**Is it production-ready?**
It's a single-operator local pilot. Next steps for production: authentication, multi-user access, contemporary data, more product categories, and a monitored retraining loop.

## Numbers to remember

| Metric | Value |
|---|---|
| Training examples | 9,000 (9 classes × 1,000) |
| Product accuracy (test) | 88.89% |
| Joint accuracy (test) | 54.25% (baseline 55.56%) |
| Validation joint accuracy, original → fine-tuned | 48% → 74% |
| Latency | ~0.95 s mean, ~1.5 s p95 on M1 |
| Model size | 1.5B params, ~986 MB Q4_K_M |
| Tests | 72 Python + 19 frontend |
