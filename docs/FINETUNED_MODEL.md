# Verified local fine-tuned model

The supplied Unsloth checkpoint-563 export is `models/Qwen2.5-1.5B-Instruct.Q4_K_M.gguf`. It contains 1.54 billion parameters, has a valid GGUF v3 header, and is 986,048,128 bytes. SHA-256: `5f4e887a39d56b79c47bb4b5f0d71d8de1e01687ac1c7217c35011b5e0cabd39`. Weights remain local and are excluded from Git.

The user completed QLoRA training in Colab and downloaded the full-model Q4_K_M export. The prepared training set contains 9,000 real historical CFPB complaints across three products and nine issue pairs. Cloud training provenance is based on the supplied export and session; the local verification independently establishes the file identity and inference behavior.

## Results

| Configuration | Cases | Product accuracy | Joint product/issue accuracy |
|---|---:|---:|---:|
| Original Qwen, constrained validation | 27 | 77.78% | 48.15% |
| Fine-tuned Qwen, constrained validation | 27 | 96.30% | 74.07% |
| Baseline, reserved test | 153 | 88.24% | 55.56% |
| Fine-tuned Qwen, reserved test | 153 | 88.89% | 54.25% |

Mean fine-tuned latency on the reserved test was 953 ms. All 153 predictions completed successfully. The small validation improvement did not translate into higher joint test accuracy. Results are historical, balanced, and limited to the fixed taxonomy. The 153 original test cases retain their test membership within the expanded 900-case split; the remaining 747 were not evaluated.

## Runtime and application

Run these in separate terminals from the project directory:

```sh
sh run_model.sh
sh run_demo.sh
```

Open http://127.0.0.1:8501. The API reports the configured engine in `/api/health`, returns `backend: slm` and the GGUF filename with each new result, and stores cases in the existing local SQLite database. Older baseline cases retain their original backend labels. For an explicit baseline demonstration, stop the app and use `COMPLAINTIQ_BACKEND=baseline sh run_demo.sh`.

The Metal server runs on localhost port 8504, with 2,048 context tokens, four CPU threads, and one inference slot. The app verifies that the expected GGUF path is loaded. It normalizes whitespace and uses the first 2,000 complaint characters, matching dataset preparation. It checks the template token budget, requests deterministic strict allowed-pair JSON decoding, and validates the output independently. No confidence score is invented. Invalid outputs and server failures produce an explicit error, never a silent baseline switch.

Priority, routing and suggested actions use rules; complaint previews are extractive. SLM LIME is disabled by default for speed. These features must not be described as learned severity prediction or SLM attribution.

Measured evidence: `artifacts/finetuned_validation_smoke.json` and `artifacts/finetuned_evaluation.json`. Reproduce the frozen test run with `.venv/bin/python -m scripts.evaluate_server` while the model server is running. To evaluate all 900 reserved cases, add `--test-file data/finetuning/test.csv --output artifacts/finetuned_evaluation_900.json` (about 15 minutes at the measured latency).

Training is reproducible with `notebooks/train_qwen25_colab.ipynb` / `scripts/train_qlora.py` (Unsloth QLoRA on `data/finetuning/training.jsonl`).
