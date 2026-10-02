# ComplaintIQ fine-tuning dataset

Prepared October 3, 2026 for Qwen2.5-1.5B-Instruct QLoRA training on a cloud GPU. No model training is started by dataset preparation.

## Source and scope

Use the official [CFPB published narratives archive](https://www.consumerfinance.gov/foia-requests/foia-electronic-reading-room/cfpb-consumer-complaint-database-narratives-archive/), December 2011 through April 2018. The archive contains 1,031,863 complaint records; only supported product/issue pairs with non-empty narratives qualify. The archive SHA-256 is `9d4fabeb5db925ce4303e81ab448f44531303a995aec1a935abc09156f2fc533`.

This historical source deliberately matches the application's existing three product families and nine issue classes. Its labels are consumer selections, not independently adjudicated facts. It does not establish performance on contemporary complaints or other product categories.

## Files and training use

| Split | Examples | Per issue category |
|---|---:|---:|
| Training | 9,000 | 1,000 |
| Validation | 900 | 100 |
| Test | 900 | 100 |

Total: 10,800 real labelled examples. The original 693 training, 144 validation and 153 test records retain their split assignments. Selected complaint dates span March 19, 2015 through April 30, 2018. The trainable sample is approximately 13 times the original training size; this is a substantial initial assignment dataset, not a guarantee of accuracy.

The separate `data/finetuning/` directory holds the larger dataset. The existing `data/training.csv`, `data/validation.csv`, `data/test.csv` and baseline evidence remain unchanged.

Upload **only `training.jsonl`** to the Unsloth training dataset field. Each line contains `messages` with a system instruction, a complaint input and the labelled assistant JSON response. Use the model's Qwen chat template and inspect the formatted preview before starting. Do not train on `validation.jsonl` or `test.jsonl`.

`validation.jsonl` is for tuning settings and selecting a checkpoint. `test.jsonl` is for the final evaluation after those decisions. CSV files retain complaint IDs, dates, original normalized narratives and the exact model input excerpt. `manifest.json` records counts, source identity, preparation rules and file hashes.

The model sees the first 2,000 characters of each normalized narrative, matching the local candidate benchmark. Some complaints lose relevant details beyond that limit. Use identical clipping and prompts when comparing original and trained checkpoints. Context length 2,048 tokens is an initial training setting; verify actual token lengths and avoid silently truncating assistant labels.

The dataset teaches product and issue classification. It contains no trained severity, routing, resolution or summary targets, and no curated out-of-domain examples; those features need separate rules or data.

The older notebook and training script still target Qwen3-4B and a different input length. They must be adapted to Qwen2.5 and this dataset before execution.

## Verification and reproduction

The generator scans the complete source and retains deterministic seed-42 hash-ranked candidate pools per class, rather than sampling only the earliest source rows. Missing/short narratives and unsupported pairs are excluded. SHA-256 hashes of case-folded, whitespace-normalized 2,000-character inputs identify exact repeats. There are zero shared IDs or input hashes across final splits, and zero original held-out IDs/inputs in training.

A bounded, approximate word-triple shingle check rejects new excerpts with verified Jaccard overlap of at least 0.95 against reserved or accepted inputs. It rejected 65 candidate near duplicates. This lexical check can miss paraphrases and is not a semantic leakage guarantee. One near-identical pair already present within the original training split remains to preserve the original data; no such pair was detected across original splits.

The final training file has 1,250 clipped narratives; validation has 141 and test has 138. Original CSV hashes and output file hashes are recorded in the manifest. All 10,800 JSONL examples are paired with labelled CSV rows for independent verification.

Reproduce using the downloaded official ZIP:

```bash
.venv/bin/python scripts/prepare_finetuning_data.py \
  --archive /path/to/CCDB_Export_1_December_2011_through_April_2018.zip \
  --output data/finetuning
```

The output directory must be empty. The generator refuses to overwrite existing datasets or silently pad a category when unique records are insufficient. The full Python suite passes 64 tests with 86% coverage; Ruff and mypy pass.
