# Fine-tuning workflow

**Status (October 4, 2026): complete.** Qwen2.5-1.5B-Instruct was fine-tuned with Unsloth QLoRA on a free Colab GPU using `data/finetuning/training.jsonl` (9,000 real CFPB complaints, nine product/issue pairs). The run was exported from checkpoint-563 as `Qwen2.5-1.5B-Instruct.Q4_K_M.gguf` (SHA-256 `5f4e887a…cabd39`) and runs locally on the M1 through llama.cpp Metal. Measured results are in [`docs/FINETUNED_MODEL.md`](../docs/FINETUNED_MODEL.md).

`train_qwen25_colab.ipynb` and `scripts/train_qlora.py` reproduce that workflow: same base model, same JSONL training file and chat template, 4-bit QLoRA (LoRA r=16 on all attention/MLP projections), smoke test first, then a resumable one-epoch run and Q4_K_M GGUF export.

1. Open the notebook in Colab or Kaggle with a free GPU runtime. Do not enable paid billing.
2. Upload/extract the project, set `PROJECT`, and mount Drive on Colab for persistent checkpoints.
3. Run the two-step smoke test, then the full run with `--export-gguf`.
4. Download the GGUF, place it in `models/`, start it with `COMPLAINTIQ_MODEL_PATH=models/Qwen2.5-1.5B-Instruct.Q4_K_M.gguf sh run_pilot.sh`, and evaluate with `.venv/bin/python -m scripts.evaluate_server` (add `--test-file data/finetuning/test.csv` for all 900 reserved cases).

Never train on `validation.jsonl` or `test.jsonl`. Weights, adapters and checkpoints are excluded from Git.

## Real dataset

The checked-in 990 narratives were retrieved on September 30, 2026 from the [official historical CFPB narrative archive](https://www.consumerfinance.gov/foia-requests/foia-electronic-reading-room/cfpb-consumer-complaint-database-narratives-archive/), December 2011–April 2018 export. The current live complaint API returned no narrative fields during verification. `data/manifest.json` records the exact archive URL, SHA-256, label normalization, class counts, sampling and split limitations.

Reproduce with:

```sh
curl -L --fail 'https://files.consumerfinance.gov/f/documents/CCDB_Export_1_December_2011_through_April_2018.zip' -o /tmp/complaintiq-archive.zip
python scripts/prepare_data.py --archive /tmp/complaintiq-archive.zip
python scripts/evaluate.py
```

The archive is approximately 128 MB; extraction streams its CSV without unpacking it to disk. Only the small sampled CSV files are committed. Exact normalized narrative duplicates are removed before splitting. Near duplicates and recurring complaint templates are not detected, so leakage remains a limitation. This is a historical, balanced demonstration sample, not a contemporary representative benchmark. Priority/actions have no trained reference labels and remain documented rules.

Baseline evaluation stores accuracy, macro precision, recall, F1, per-class support and confusion matrices in `artifacts/evaluation.json`. Macro metrics use ground-truth labels; abstentions count as missed predictions, with their rate and confusion-matrix column reported separately. The fine-tuned SLM evaluation is stored separately in `artifacts/finetuned_evaluation.json`.

The prepared cloud training and comparison clip complaints to 4,000 characters. The application accepts up to 6,000 characters. Before comparing cloud results with application GGUF results, use matching input clipping and generation settings; the current baseline artifact uses the full held-out text.
