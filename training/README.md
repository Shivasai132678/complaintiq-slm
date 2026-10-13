# Training the ComplaintIQ model

This folder holds the code that produced `models/complaintiq-qwen3-4b-Q4_K_M.gguf`:
a 4-bit QLoRA fine-tune of **Qwen3-4B-Instruct-2507** as a 10-class complaint classifier
(9 supported product/issue pairs plus `Unknown / Needs review`), exported to a Q4_K_M GGUF
that the app serves through llama.cpp.

You do **not** need any of this to run the app. Training needs an NVIDIA GPU (the published
run used an RTX 4070, 12 GB). The one-click Windows kit that was used for that run, with its
`.bat`/PowerShell runners and notebook, is preserved on the
[`windows-pc-kit`](https://github.com/Shivasai132678/complaintiq-slm/tree/windows-pc-kit) branch.

## Layout

| Path | What it is |
|---|---|
| `src/prepare_dataset.py` | Builds the train/validation/test/check splits from the official CFPB export (runs on the Mac, standard library only) |
| `src/train_qwen3.py` | QLoRA training: `--mode dryrun`, `speedtest` or `train` |
| `src/evaluate_qwen3.py` | Evaluates an adapter (or the untuned base) on the test and check sets |
| `src/export_gguf.py` | Merges the adapter, converts to GGUF and quantizes |
| `src/gguf_eval.py` | Evaluates a GGUF through `llama-server` exactly the way the app calls it |
| `src/ckit_*.py` | Shared labels, prompt, constrained decoding and metrics (also tested by `tests/test_training.py`) |
| `data/manifest.json` | Data source, archive hash, split policy and per-class counts |
| `results/qwen3-4b-main/` | Settings, loss log, summary and evaluation of the published run |

Generated CSV splits, the base model, checkpoints and the adapter are not committed (see `.gitignore`).

## Steps

```sh
# 1. Data (Mac or any machine; the archive is the official CFPB export recorded in data/manifest.json)
.venv/bin/python training/src/prepare_dataset.py --archive data/cfpb_raw/<complaints>.csv.zip --output training/data

# 2. On the GPU machine (Python 3.11)
python -m venv .venv-train && . .venv-train/bin/activate
pip install -r training/requirements.txt --extra-index-url https://download.pytorch.org/whl/cu126
huggingface-cli download Qwen/Qwen3-4B-Instruct-2507 --local-dir training/model/Qwen3-4B-Instruct-2507

python training/src/train_qwen3.py --mode dryrun
python training/src/train_qwen3.py --mode train --run-name qwen3-4b-main --max-steps 950 --batch-size 2 --grad-accum 8

# 3. Export (needs a llama.cpp checkout for convert_hf_to_gguf.py and llama-quantize)
git clone https://github.com/ggml-org/llama.cpp training/tools/llama.cpp   # then build llama-quantize
python training/src/export_gguf.py --adapter training/results/qwen3-4b-main/final_adapter
```

`export_gguf.py` copies the finished GGUF into `models/`, where `run_pilot.sh` picks it up.

## Published run

950 steps (effective batch 16, about 15,200 of 70,162 training rows), 2 h 1 min on an RTX 4070,
final training loss 0.057, peak VRAM 15.3 GB. Exact settings are in
`results/qwen3-4b-main/run_config.json`.

| Test set (3,000 rows, Feb-Jul 2026) | Result |
|---|---|
| 10-class accuracy | 64.50% |
| Macro F1 | 64.95% |
| Product accuracy | 90.27% |
| Out-of-scope precision / recall | 82.35% / 65.33% |
| Invalid replies | 0 |

Full per-class tables: [`results/qwen3-4b-main/eval/results.md`](results/qwen3-4b-main/eval/results.md).
The Q4_K_M GGUF (SHA-256 `9a810438…172211`) scored 59.7% on the same first 300 test rows versus
64.7% for the unquantized adapter, so quantization costs some accuracy.
