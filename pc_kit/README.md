# ComplaintIQ on a Windows PC: train Qwen3-4B, then run the app

The whole SLM Project runs on the PC: **first training, then the app with the new model, then
(later) the video.** `pc_kit\` holds everything needed to fine-tune **Qwen3-4B-Instruct-2507** with 4-bit QLoRA as
ComplaintIQ's 10-class complaint classifier on a freshly installed Windows 11 PC with an RTX 4070
(12 GB). Nothing needs to be downloaded on the PC. The data was prepared on the Mac, the model
files are included, and all installers and Python wheels are bundled.

**Target PC:** i7-14700K, 32 GB RAM, RTX 4070 12 GB, Windows 11 Pro, nothing installed.
**You need:** the project on a USB drive (exFAT or NTFS, ~14 GB), admin rights for the driver
and VC++ runtime prompts, and about 50 GB free disk on the PC.

**On the Mac, before leaving:** `sh pc_kit/mac_prep/make_pc_bundle.sh /Volumes/<USB>/SLMProject`
copies the full project (13.9 GB; see the lite option below) without the Mac `.venv` (756 MB), `frontend/node_modules` (144 MB),
the raw 1.3 GB CFPB zip (the prepared splits in `pc_kit/data` replace it), the unused base Qwen2.5
GGUF (1.1 GB), `upstream/`, caches and `.DS_Store` files. The whole folder is 17.3 GB.
It refreshes `frontend/dist`, so the PC needs no Node.js for the app.

## Two ways to get the project onto the PC

| Bundle | Command on the Mac | Size | Needs on the PC |
|---|---|---|---|
| **Lite** (recommended when copying over the network) | `sh pc_kit/mac_prep/make_pc_bundle.sh --lite --zip ~/Desktop/SLMProject` | ~0.6 GB (zip ~0.5 GB) | Internet: it downloads ~9 GB (Qwen3-4B 7.5 GB from Hugging Face, llama.cpp, installers) plus ~3 GB of Python packages |
| **Full** (works offline) | `sh pc_kit/mac_prep/make_pc_bundle.sh --zip /Volumes/<USB>/SLMProject` | ~13.9 GB | Nothing |

Both leave out the raw CFPB zip, the Mac `.venv`, `node_modules`, caches and the unused base model.
With the lite bundle, `RUN_ALL.bat` (step 1) downloads whatever is missing using `pc_kit\downloads.json`
and checks every file's SHA-256 before use; Python packages come from PyPI and download.pytorch.org
at the exact pinned versions. Files already present are never downloaded again.

**If a download fails** (no internet, Hugging Face blocked, a checksum mismatch), setup stops and
lists the missing files. Copy just those folders from the full bundle by USB into the same place,
for example `pc_kit\model\Qwen3-4B-Instruct-2507\` (7.5 GB), `pc_kit\wheels\` (2.5 GB),
`pc_kit\installers\`, `pc_kit\tools\llama-bin\`, then double-click `RESUME_ALL.bat`.

## One click: `RUN_ALL.bat`

Copy the project to `C:\SLMProject` and double-click **`C:\SLMProject\RUN_ALL.bat`**. It runs every
step below by itself, in order, and stops with a clear message at the first failure:

1. Setup: checksums, NVIDIA driver, VC++ runtime, Python 3.11, packages, GPU and bitsandbytes check
2. Dry run
3. Speed test, then it picks the number of training steps so training fits in 7 hours
   (a full epoch if it fits); the 7-hour safety stop stays on
4. Training, with checkpoints and evaluation on the test and check sets
5. GGUF export, copy into `models\`, and the 300-row llama-server check
6. App setup (Python 3.12, packages, tests)
7. Starts the app at http://127.0.0.1:8501 in the same window

- **See where it is:** open `logs\run_all_status.txt` (the current step, training step/loss and the
  latest validation accuracy, refreshed every minute). Everything is logged to `logs\run_all.log`.
- **After a crash, reboot or fixed error:** double-click **`RESUME_ALL.bat`**. Finished steps are
  skipped and training continues from its newest checkpoint. (Running `RUN_ALL.bat` again does the
  same.) To start over completely, delete `logs\run_all_state.json`.
- **Windows prompts you'll see:** admin (UAC) prompts for the NVIDIA driver and the VC++ runtime.
  If a driver had to be installed, it stops and asks you to restart Windows, and `RESUME_ALL.bat`
  starts by itself after you log in.
- **If the GPU check fails** (step 1 or 2): it stops; nothing else runs. Read the end of
  `logs\run_all.log` and `pc_kit\results\setup_log.txt`. Driver problems: restart, then
  `RESUME_ALL.bat`. If bitsandbytes itself will not work after ~30 minutes, the WSL2 fallback
  below **needs you to act** (internet, admin, a restart and a few commands). `RUN_ALL` cannot do it
  for you.
- The whole run takes roughly 9-10 hours (about 1 h of setup, checks and export plus up to 7 h of
  training). The window has to stay open; it keeps Windows from sleeping while it runs.
- Every step can still be run by hand with the separate `.bat` files described below.

---

## The day, in order

| # | Step | What to do | Time |
|---|------|------------|------|
| 0 | Copy | Copy the project folder to **`C:\SLMProject`** (short path, avoids Windows path-length errors); everything below runs in `C:\SLMProject\pc_kit` | 10-15 min |
| 1 | Setup | Double-click **`setup_windows.bat`** | 20-30 min |
| 2 | Dry run | Double-click **`run_dryrun.bat`**. Must end with `DRY RUN PASSED` | 5-10 min |
| 3 | Speed test | Double-click **`run_speedtest.bat`**. Read the `recommendation` line | 10-15 min |
| 4 | Train | Double-click **`run_train.bat`** (add `--max-steps N` if the speed test says so) | 3-7 h |
| 5 | Evaluate | Runs automatically at the end of training. Read `results\qwen3-4b-main\eval\results.md` | 10-15 min |
| 6 | Export | Double-click **`run_export.bat`** (GGUF for the app + check on 300 rows) | 20-30 min |
| 7 | Copy back | `copy_back.bat E:\complaintiq_results` (your USB drive), a safety copy of the results | 5 min |
| 8 | App | `C:\SLMProject\setup_app_windows.bat`, put the GGUF in `models\`, then `run_pilot.bat` (see "Run the app on the PC") | 15 min |
| 9 | Video | Later, after the app works (see "Video, later") | - |

Prefer the notebook? Run `start_notebook.bat`, which opens `notebooks\train_qwen3_windows.ipynb`
with the same steps. For the long training step, the `.bat` window is safer than a browser tab.

### 1. Setup (`setup_windows.bat`)

It runs `setup_windows.ps1`, which is safe to re-run and logs to `results\setup_log.txt`:

1. Verifies the SHA-256 of every file against `CHECKSUMS.sha256` (`verify_checksums.ps1`).
2. Checks the NVIDIA driver with `nvidia-smi`. If it is missing or older than 560, it starts the
   bundled driver installer (`installers\nvidia-617.42-desktop-...exe`, choose *Express*), then asks
   you to **restart Windows and run setup again**.
3. Installs the Microsoft Visual C++ runtime if missing (admin prompt).
4. Installs Python 3.11.9 for the current user (no admin, not added to PATH).
5. Creates `.venv` and installs the pinned packages **offline** from `wheels\`
   (`requirements-windows.lock.txt`, 119 packages).
6. Runs `src\env_check.py`: CUDA, bf16, a real bitsandbytes 4-bit forward/backward on the GPU,
   model shards, tokenizer, data files, free disk and `llama-server.exe`. It must print `READY`.

Git is not needed: nothing is cloned on the PC.

### 2. Dry run (`run_dryrun.bat`)

Loads Qwen3-4B in 4-bit, trains 5 steps on 64 rows, saves the adapter, reloads it from disk and
evaluates 32 validation rows with constrained decoding. Output: `results\dryrun-Qwen3-4B-Instruct-2507\`.

### 3. Speed test (`run_speedtest.bat`)

200 real training steps. `results\speedtest-Qwen3-4B-Instruct-2507\speedtest.json` reports
seconds/step, tokens/second, peak VRAM, `projected_hours_per_epoch`, `steps_that_fit_in_Nh` and a
`recommendation`:

- Full epoch fits in 7 h: just run `run_train.bat`.
- It does not fit: run `run_train.bat --max-steps <steps_that_fit_in_7h>` (or keep the default
  7-hour budget, which stops cleanly and saves when time runs out; the LR schedule is then not
  finished, so a fixed `--max-steps` is slightly better).
- Peak VRAM under ~8 GB: `--batch-size 8 --grad-accum 2` is usually a bit faster (same effective batch).

### 4. Train (`run_train.bat`)

Defaults (all overridable, see `python src\train_qwen3.py --help`):

| Setting | Default |
|---|---|
| Model | Qwen3-4B-Instruct-2507, 4-bit NF4, double quant, bf16 compute, SDPA attention |
| LoRA | r=16, alpha=32, dropout 0.05, all attention + MLP projections |
| Max length | 512 tokens (prompt + answer); the complaint text is cut to fit, never the prompt |
| Batch | 4 per step x 4 accumulation = 16 sequences per optimizer step |
| Optimizer | AdamW, LR 1e-4, cosine, 3% warmup, grad-norm clip 1.0, gradient checkpointing |
| Length | 1 epoch (~4,400 steps), 7-hour safety budget |
| Checkpoints | every 250 steps, newest 3 kept, in `results\qwen3-4b-main\checkpoints\` |
| Validation | every 500 steps: loss on 400 rows + accuracy on 300 rows (constrained decoding) |
| Windows | `dataloader_num_workers=0`, no `torch.compile`, everything offline |

Re-running `run_train.bat` **resumes from the newest checkpoint** (power cut, closed window, etc.).
`--no-resume` starts over. Progress and timestamped events: `results\qwen3-4b-main\train_log.jsonl`.
At the end it saves `final_adapter\` and evaluates it (step 5).

### 5. Evaluate (automatic, or `run_eval.bat`)

The new model is evaluated with greedy decoding **constrained to the ten valid replies** (a token
trie), which mirrors the app's strict JSON-schema decoding. Input is the app's exact prompt with the
full 2,000-character excerpt (up to 1,024 prompt tokens).

Outputs in `results\qwen3-4b-main\eval\`:

- `test_predictions.json`, `check_predictions.json`: every row's prediction plus accuracy, macro
  precision/recall/F1, weighted F1, product accuracy, in-scope joint accuracy, out-of-scope
  precision/recall, per-class scores and the confusion matrix.
- `results.md` / `results.json`: the summary to report: 10-class accuracy, macro and weighted F1,
  product accuracy, out-of-scope precision/recall, accuracy per check-set source and per-class scores.

To evaluate a checkpoint instead: `run_eval.bat --adapter results\qwen3-4b-main\checkpoints\checkpoint-3000`.

### 6. Export for the app (`run_export.bat`)

`src\export_gguf.py` merges the adapter into the bf16 base on the CPU (~10 GB RAM), converts it with
the bundled llama.cpp b11496 converter and quantizes it with `llama-quantize.exe` to
**`results\qwen3-4b-main\export\complaintiq-qwen3-4b-Q4_K_M.gguf`** (~2.5 GB, SHA-256 in
`export_manifest.json`). Intermediates (~16 GB) are deleted afterwards. Then `src\gguf_eval.py`
starts the bundled CUDA `llama-server.exe` and classifies 300 test rows with the app's exact
request; accuracy should be within a couple of points of the adapter's.

### 7. Copy back (`copy_back.bat <destination>`)

Copies `results\` to the destination (for example `E:\complaintiq_results`), skipping the merged
model and f16 GGUF. It keeps the final adapter, the newest checkpoint of each run (to continue
training later), the GGUF, evaluations, logs and `setup_log.txt`. Then check that the GGUF and
`eval\results.md` arrived. Typical size: ~3 GB.

---

## If something goes wrong

**bitsandbytes fails (env check or dry run).** Give it about 30 minutes: re-run
`run_env_check.bat`, check the driver version (`nvidia-smi`, needs 560+), restart after a driver
install. If it still fails, use the WSL2 fallback below.

**WSL2 fallback (needs internet on the PC and admin).**

1. In an admin PowerShell: `wsl --install -d Ubuntu-24.04`, restart, create the Ubuntu user.
   (Virtualization must be enabled in the BIOS. The Windows NVIDIA driver also serves WSL; do not
   install a Linux driver.)
2. In Ubuntu: `sudo apt update && sudo apt install -y python3-venv python3-pip`
3. Copy the kit into the Linux filesystem (much faster than `/mnt/c`):
   `cp -r /mnt/c/SLMProject/pc_kit ~/ckit && cd ~/ckit` (you can skip `wheels`, `installers`, `tools`).
4. `python3 -m venv .venv && . .venv/bin/activate`
   `pip install -r requirements-wsl.txt --extra-index-url https://download.pytorch.org/whl/cu126`
5. Same commands, Linux paths: `python src/train_qwen3.py --mode dryrun`, then `--mode speedtest`,
   then `--mode train --run-name qwen3-4b-main --time-budget-hours 7`.
6. Copy `~/ckit/results/qwen3-4b-main` back to `C:\SLMProject\pc_kit\results\` (Explorer: `\\wsl$\Ubuntu-24.04\home\<user>\ckit`)
   and run `run_export.bat` on Windows (the export uses the CPU and the bundled Windows llama.cpp tools).

**Out of GPU memory.** `run_train.bat --batch-size 2 --grad-accum 8` (same effective batch).

**Training interrupted.** Run `run_train.bat` again; it resumes from the newest checkpoint.

**Out of time before the epoch ends.** The 7-hour budget saves a checkpoint and continues to the
final adapter and evaluation automatically. You can also stop with Ctrl+C and evaluate/export the
newest checkpoint: `run_eval.bat --adapter results\qwen3-4b-main\checkpoints\checkpoint-N`, then
`run_export.bat results\qwen3-4b-main\checkpoints\checkpoint-N`.

**Export fails.** Copy `final_adapter\` back anyway (it is the trained model, ~130 MB). The merge and
conversion can be redone later on any machine with the same scripts.

---

## Run the app on the PC (after training)

1. **Install the app** (offline, once): double-click `C:\SLMProject\setup_app_windows.bat`. It
   installs Python 3.12.10 for the current user, creates `C:\SLMProject\.venv` from
   `pc_kit\wheels_app` (`requirements-app-windows.lock.txt`, the same versions as on the Mac) and
   runs the test suite. The React frontend is already built (`frontend\dist`).
2. **Plug in the new model:** copy
   `pc_kit\results\qwen3-4b-main\export\complaintiq-qwen3-4b-Q4_K_M.gguf` to `C:\SLMProject\models\`.
   `scripts\launch_pilot.py` uses it automatically when it is there (otherwise the old Qwen2.5
   GGUF), and finds the CUDA `llama-server.exe` in `pc_kit\tools\llama-bin`. Override with
   `set COMPLAINTIQ_MODEL_PATH=...` or `set COMPLAINTIQ_LLAMA_SERVER=...`.
3. **Start it:** double-click `run_pilot.bat`. Open http://127.0.0.1:8501 (logs in `data\logs`).
   `run_demo_seed.bat` fills an empty dashboard with labelled public demo complaints.
4. **Evaluation card in the app** (while `run_pilot.bat` is running), in a second window from `C:\SLMProject`:
   `.venv\Scripts\python.exe -m scripts.evaluate_server --model-path models\complaintiq-qwen3-4b-Q4_K_M.gguf --output artifacts\qwen3_evaluation.json`
   then restart `run_pilot.bat`; it shows `artifacts\qwen3_evaluation.json` for the Qwen3 model.
   Edit that file's `limitations` text, which still describes the old Qwen2.5 export.

The prompt, labels and JSON reply format are exactly the app's (`src/ckit_common.py` is tested
against `complaintiq/server_model.py`), so no app code changes are needed for the new model.
The app's scope gate still runs before the model; the new model also answers
`Unknown / Needs review` for out-of-scope text itself.

The same steps work on the Mac: copy the GGUF to `models/` and run `sh run_pilot.sh` (it also
prefers the Qwen3 GGUF; Homebrew `llama-server` is used there).

**Git on the PC (optional):** `installers\Git-2.56.0.2-64-bit.exe` installs Git so you can commit
from the PC. The `.git` folder is included in the copy; pushing needs your GitHub login.

## Video, later

Not set up in this kit. The reel source is in `artifacts\video\reel-source` (Remotion + Kokoro
voice-over). Rendering it on the PC needs internet to install Node.js 22 LTS (nodejs.org), ffmpeg
(winget install Gyan.FFmpeg), the Remotion packages (`npm install`) and the Kokoro model files.
It also needs fresh screenshots of the app in `public\shots\` and an updated voice-over script
(the current one quotes the old Qwen2.5 numbers).

---

## What is in this folder

| Path | Contents |
|---|---|
| `setup_windows.bat` / `.ps1`, `verify_checksums.ps1` | One-click offline setup and checksum verification |
| `run_*.bat`, `start_notebook.bat`, `copy_back.bat` | One-click steps; `scripts_win\` holds shared settings |
| `notebooks\train_qwen3_windows.ipynb` | The same steps as a notebook |
| `src\` | `train_qwen3.py` (dry run / speed test / train), `evaluate_qwen3.py`, `export_gguf.py`, `gguf_eval.py`, `env_check.py`, shared `ckit_*.py` |
| `data\` | `train.csv`, `validation.csv`, `test.csv`, `check.csv`, `manifest.json` (see Data below) |
| `model\Qwen3-4B-Instruct-2507\` | Model weights and tokenizer, revision `cdbee75f`, SHA-256 checked against Hugging Face |
| `installers\` | Python 3.11.9 (training), Python 3.12.10 (app), VC++ 2015-2022 x64 runtime, NVIDIA 617.42 Game Ready driver, Git 2.56 |
| `wheels_app\` | Windows wheels for the app (Python 3.12): FastAPI, scikit-learn, LIME, Streamlit, pytest, ... |
| `wheels\` | All Windows wheels for Python 3.11 (PyTorch 2.10.0 CUDA 12.6, bitsandbytes 0.50.2, transformers 5.19.0, peft 0.21.2, accelerate 1.15.0, JupyterLab) |
| `tools\llama-bin\` | llama.cpp b11496 Windows CUDA 12.4 binaries (llama-server, llama-quantize) |
| `tools\llama.cpp-convert\` | llama.cpp b11496 `convert_hf_to_gguf.py` + `gguf-py` |
| `mac_prep\` | Mac-side scripts: data prep, `make_pc_bundle.sh`, checksums |
| `requirements-windows*.txt`, `requirements-wsl.txt` | Pinned package lists |
| `CHECKSUMS.sha256` | SHA-256 of every file above |
| `results\` | Empty; everything the PC produces goes here |

## Data

**Source.** The official CFPB Consumer Complaint Database export (`complaints.csv.zip`, public
domain). On 2026-10-08 the live CFPB file no longer contained consumer narratives, so the kit uses
the same official export as of 2026-08-11 from a public mirror
([vivekkopthsd/cfpb-consumer-complaints](https://huggingface.co/datasets/vivekkopthsd/cfpb-consumer-complaints),
revision `280afed1`, SHA-256 `d9223948...a6658`, matches the mirror's published hash). It was
cross-checked against the Internet Archive's 2026-08-15 capture of the official URL: of 2,816,223
complaints present in both, 99.93% are identical in date, product, sub-product, issue, sub-issue and
narrative; the other 1,966 differ only in narrative text. Details: `data/manifest.json`.

**Classes (10).** The app's nine product/issue pairs plus `Unknown / Needs review` (out of scope).
Old (2011-2017) and new (2017+) CFPB issue names are mapped onto the nine pairs in
`src/ckit_common.py` (for example, new "Managing an account" with sub-issue "Deposits and
withdrawals" becomes *Deposits and withdrawals*; "Problem with a purchase shown on your statement"
becomes *Billing disputes*; "Other features, terms, or problems" becomes credit card *Other*).
Complaints about the three supported products with other issues (for example "Getting a credit
card") are left out entirely. Out of scope = other CFPB products (debt collection, mortgage,
student loan, vehicle/consumer loan, payday/personal loan, money transfer, prepaid card, debt
management), sampled evenly by family, plus the project's 54 authored non-financial "tune"
examples (x3).

**Splits (time-based, deduplicated).** 3,510,009 eligible narratives (2015-03 to 2026-07).

| Split | Months | Rows | Per class |
|---|---|---|---|
| train | 2015-03 to 2025-11 | 70,162 | 7,000 (out of scope 7,162) |
| validation | 2025-12 to 2026-01 | 1,938 | 200 (Improper use: 138, all available) |
| test | 2026-02 to 2026-07 (newest) | 3,000 | 300 |
| check (held out) | earlier project splits | 1,407 | original 153-case test + 1,200 scope-gate other-product test rows + 54 authored unrelated |

Narratives are sparse in 2026, so the test window needed six months to reach 300 per class.
Exact duplicates are removed across all splits (test wins over validation over train), check-set
IDs and texts are reserved, and training rows that near-duplicate any evaluation row (shingle
Jaccard >= 0.9) were dropped (3,052). Input is the app's whitespace-normalized first 2,000
characters. With the Qwen3 tokenizer the training examples average ~370 tokens; about 25% of
complaints are cut to fit 512 tokens (the prompt itself is ~150 tokens).

## Defaults chosen (not specified in the plan)

- **Generative classifier, not a classification head.** The model is fine-tuned to reply with the
  app's exact JSON (`{"product": ..., "issue": ...}`, or `Unknown`/`Needs review`), using the app's
  exact system/user prompt. This keeps it drop-in compatible with the existing llama.cpp GGUF path
  and strict JSON-schema decoding; evaluation uses equivalent constrained decoding.
- Loss only on the answer tokens (prompt masked).
- 7,000 training complaints per class (~70k total), 200 validation and 300 test per class.
- LoRA r=16/alpha=32 on all projections, LR 1e-4 cosine, batch 4 x 4 accumulation, 1 epoch,
  7-hour safety budget, checkpoints every 250 steps.
- Evaluation prompt budget 1,024 tokens (the app's full 2,000-character excerpt) although training
  uses 512; this matches what the app will send.
- PyTorch 2.10.0 + CUDA 12.6 wheels (needs NVIDIA driver 560+; the bundled 617.42 driver covers it).
  llama.cpp b11496 CUDA 12.4 build for export/serving checks.
- Python 3.11.9 (last 3.11 release with a Windows installer), installed per user without PATH changes.
- TRL is not used: plain `transformers.Trainer` with a small collator is simpler and avoids TRL API churn.
- No SHAP/LIME for the 4B model: one LIME explanation needs hundreds of model calls. The app keeps its
  baseline LIME explanation.
- The Qwen3-1.7B fallback was dropped at your request; WSL2 is the only fallback.
