# Training later on a free GPU

`train_qwen3_colab.ipynb` is a prepared, unexecuted training notebook. The working assignment application uses the measured classical baseline until you explicitly configure a local GGUF. No SLM has been fine-tuned or evaluated in this repository yet.

1. Open the notebook in Google Colab or Kaggle and select a free GPU runtime. Free GPU access is availability/quota dependent; do not enable paid billing.
2. Upload/extract the project, install the notebook dependencies, set `PROJECT` to the extracted path, and mount Drive on Colab for persistent output.
3. Run the two-step smoke test first. Then train 120 optimizer steps in a separate `full` output directory. Resume only a matching run; save/download outputs before ending a session.
4. Compare original and fine-tuned generation on the same untouched `data/test.csv`. Save `slm_evaluation.json`; actual metrics must be measured, never copied from expected results.
5. Export Q4_K_M GGUF on the cloud machine and download it. No large model download or training is necessary on the M1 Mac during app development. Follow root README to enable local inference later.

This notebook adapts APIs from [Unsloth's official Qwen3 4B Instruct notebook](https://colab.research.google.com/github/unslothai/notebooks/blob/main/nb/Qwen3_(4B)-Instruct.ipynb). Runtime compatibility and GPU memory are not yet verified. If Unsloth installation changes, use its official install cells. Checkpoint folders, adapter, tokenizer, taxonomy, environment versions, run status, and held-out evaluation should be retained together.

## Real dataset

The checked-in 990 narratives were retrieved on September 30, 2026 from the [official historical CFPB narrative archive](https://www.consumerfinance.gov/foia-requests/foia-electronic-reading-room/cfpb-consumer-complaint-database-narratives-archive/), December 2011–April 2018 export. The current live complaint API returned no narrative fields during verification. `data/manifest.json` records the exact archive URL, SHA-256, label normalization, class counts, sampling and split limitations.

Reproduce with:

```sh
curl -L --fail 'https://files.consumerfinance.gov/f/documents/CCDB_Export_1_December_2011_through_April_2018.zip' -o /tmp/complaintiq-archive.zip
python scripts/prepare_data.py --archive /tmp/complaintiq-archive.zip
python scripts/evaluate.py
```

The archive is approximately 128 MB; extraction streams its CSV without unpacking it to disk. Only the small sampled CSV files are committed. Exact normalized narrative duplicates are removed before splitting. Near duplicates and recurring complaint templates are not detected, so leakage remains a limitation. This is a historical, balanced demonstration sample, not a contemporary representative benchmark. Priority/actions have no trained reference labels and remain documented rules.

Baseline evaluation stores accuracy, macro precision, recall, F1, per-class support and confusion matrices in `artifacts/evaluation.json`. Macro metrics use ground-truth labels; abstentions count as missed predictions, with their rate and confusion-matrix column reported separately. The SLM comparison is pending.

The prepared cloud training and comparison clip complaints to 4,000 characters. The application accepts up to 6,000 characters. Before comparing cloud results with application GGUF results, use matching input clipping and generation settings; the current baseline artifact uses the full held-out text.
