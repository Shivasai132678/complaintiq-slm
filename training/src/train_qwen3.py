"""QLoRA fine-tuning of Qwen3-4B-Instruct-2507 as a 10-class ComplaintIQ classifier.

Plain transformers + peft + bitsandbytes (no Unsloth), portable
(dataloader_num_workers=0, no torch.compile, everything offline).

Modes
  dryrun     load model in 4-bit, run 5 optimizer steps on 64 rows, evaluate 32
             rows, save and reload the adapter. Proves the whole pipeline works.
  speedtest  ~200 training steps on real data; reports seconds/step, tokens/s,
             peak VRAM and the projected time for a full epoch.
  train      full run with checkpoints, periodic validation, a time budget,
             automatic resume, then test + check-set evaluation (eval\\results.md).

Examples (from the kit folder, with the venv active):
  python src\\train_qwen3.py --mode dryrun
  python src\\train_qwen3.py --mode speedtest
  python src\\train_qwen3.py --mode train --run-name qwen3-4b-main --time-budget-hours 7
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "src"))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("BITSANDBYTES_NOWELCOME", "1")

from ckit_data import PadCollator, build_training_examples, read_rows  # noqa: E402

TARGET_MODULES = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]


def log_event(log_file: Path, **fields: Any) -> None:
    """Append a timestamped JSON line (agent/debug log)."""
    fields = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), **fields}
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(fields) + "\n")
    print(json.dumps(fields), flush=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--mode", choices=["dryrun", "speedtest", "train"], required=True)
    p.add_argument("--model-dir", type=Path, default=KIT / "model" / "Qwen3-4B-Instruct-2507")
    p.add_argument("--data-dir", type=Path, default=KIT / "data")
    p.add_argument("--results-dir", type=Path, default=KIT / "results")
    p.add_argument("--run-name", default=None, help="Folder under results/ (default: <mode>-<model>)")
    p.add_argument("--max-length", type=int, default=512, help="Max training tokens (prompt+answer)")
    p.add_argument("--eval-max-prompt-tokens", type=int, default=1024,
                   help="Prompt budget at evaluation (1024 fits the app's full 2,000-character excerpt)")
    p.add_argument("--epochs", type=float, default=1.0)
    p.add_argument("--max-steps", type=int, default=-1)
    p.add_argument("--speedtest-steps", type=int, default=200)
    p.add_argument("--time-budget-hours", type=float, default=0.0,
                   help="Stop training cleanly (with a saved checkpoint) after this many hours; 0 = no limit")
    p.add_argument("--batch-size", type=int, default=4)
    p.add_argument("--grad-accum", type=int, default=4)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--warmup-fraction", type=float, default=0.03)
    p.add_argument("--lora-r", type=int, default=16)
    p.add_argument("--lora-alpha", type=int, default=32)
    p.add_argument("--lora-dropout", type=float, default=0.05)
    p.add_argument("--no-4bit", action="store_true",
                   help=argparse.SUPPRESS)  # bf16 LoRA without bitsandbytes; used for Mac smoke tests
    p.add_argument("--save-steps", type=int, default=250)
    p.add_argument("--eval-steps", type=int, default=500)
    p.add_argument("--eval-loss-rows", type=int, default=400, help="Validation rows for eval loss")
    p.add_argument("--eval-acc-rows", type=int, default=300, help="Validation rows for accuracy at each eval")
    p.add_argument("--eval-batch-size", type=int, default=16)
    p.add_argument("--train-limit", type=int, default=0, help="Use only the first N training rows")
    p.add_argument("--skip-final-eval", action="store_true")
    p.add_argument("--no-resume", action="store_true", help="Start fresh even if checkpoints exist")
    p.add_argument("--allow-cpu", action="store_true", help=argparse.SUPPRESS)  # Mac smoke tests only
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args(argv)


def load_model(args: argparse.Namespace) -> tuple[Any, Any]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(args.model_dir)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = "<|endoftext|>"
    cuda = torch.cuda.is_available()
    if not cuda and not args.allow_cpu:
        raise SystemExit("CUDA is not available. Run src\\env_check.py and check the NVIDIA driver.")
    kwargs: dict[str, Any] = {"dtype": torch.bfloat16 if cuda else torch.float32}
    if cuda:
        kwargs["device_map"] = {"": 0}
        kwargs["attn_implementation"] = "sdpa"
    if not args.no_4bit:
        from transformers import BitsAndBytesConfig

        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
    model = AutoModelForCausalLM.from_pretrained(args.model_dir, **kwargs)
    model.config.use_cache = False
    return model, tokenizer


def add_lora(model: Any, args: argparse.Namespace) -> Any:
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

    if not args.no_4bit:
        model = prepare_model_for_kbit_training(
            model,
            use_gradient_checkpointing=True,
            gradient_checkpointing_kwargs={"use_reentrant": False},
        )
    else:
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        model.enable_input_require_grads()
    config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules=TARGET_MODULES,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, config)
    model.print_trainable_parameters()
    return model


def make_callbacks(args: argparse.Namespace, run_dir: Path, tokenizer: Any, val_rows: list[dict[str, str]]):
    from transformers import TrainerCallback

    log_path = run_dir / "train_log.jsonl"

    class Monitor(TrainerCallback):
        """Timestamped logs, time budget, VRAM, and validation accuracy at each eval."""

        def __init__(self) -> None:
            self.started = time.time()
            self.step_started = time.time()

        def on_log(self, targs, state, control, logs=None, **kwargs):
            import torch

            extra = {}
            if torch.cuda.is_available():
                extra["vram_peak_gb"] = round(torch.cuda.max_memory_allocated() / 2**30, 2)
            log_event(log_path, event="log", step=state.global_step, elapsed_s=round(time.time() - self.started), **(logs or {}), **extra)

        def on_step_end(self, targs, state, control, **kwargs):
            if args.time_budget_hours and time.time() - self.started > args.time_budget_hours * 3600:
                log_event(log_path, event="time_budget_reached", step=state.global_step)
                control.should_save = True
                control.should_training_stop = True
            return control

        def on_evaluate(self, targs, state, control, model=None, **kwargs):
            if not args.eval_acc_rows or model is None:
                return
            from ckit_eval import predict
            from ckit_metrics import classification_report

            try:
                rows = val_rows[: args.eval_acc_rows]
                preds = predict(model, tokenizer, rows, max_prompt_tokens=args.eval_max_prompt_tokens,
                                batch_size=args.eval_batch_size, progress=False)
                report = classification_report([r["label"] for r in rows], [p["predicted"] for p in preds])
                log_event(log_path, event="val_accuracy", step=state.global_step, rows=len(rows),
                          accuracy=report["accuracy"], macro_f1=report["macro_f1"],
                          in_scope_joint=report["in_scope_joint_accuracy"])
            except Exception as error:  # never lose a training run to an eval problem
                log_event(log_path, event="val_accuracy_failed", step=state.global_step, error=repr(error))

    return [Monitor()]


def latest_checkpoint(run_dir: Path) -> str | None:
    checkpoints = sorted(
        (p for p in (run_dir / "checkpoints").glob("checkpoint-*") if p.is_dir()),
        key=lambda p: int(p.name.split("-")[-1]),
    )
    return str(checkpoints[-1]) if checkpoints else None


def run(args: argparse.Namespace) -> dict[str, Any]:
    import torch
    from transformers import Trainer, TrainingArguments, set_seed

    set_seed(args.seed)
    model_tag = args.model_dir.name
    run_dir = args.results_dir / (args.run_name or f"{args.mode}-{model_tag}")
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "train_log.jsonl"
    (run_dir / "run_config.json").write_text(
        json.dumps({k: str(v) for k, v in vars(args).items()}, indent=2), encoding="utf-8"
    )
    log_event(log_path, event="start", mode=args.mode, model=model_tag, python=platform.python_version(),
              torch=torch.__version__, cuda=torch.cuda.is_available(),
              gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)

    train_rows = read_rows(args.data_dir / "train.csv")
    val_rows = read_rows(args.data_dir / "validation.csv")
    random.Random(args.seed).shuffle(val_rows)
    if args.mode == "dryrun":
        train_rows, val_rows = train_rows[:64], val_rows[:32]
    elif args.train_limit:
        train_rows = train_rows[: args.train_limit]

    load_started = time.time()
    model, tokenizer = load_model(args)
    log_event(log_path, event="model_loaded", seconds=round(time.time() - load_started, 1),
              vram_gb=round(torch.cuda.memory_allocated() / 2**30, 2) if torch.cuda.is_available() else None)
    model = add_lora(model, args)

    tok_started = time.time()
    train_examples, stats = build_training_examples(tokenizer, train_rows, args.max_length)
    eval_examples, _ = build_training_examples(tokenizer, val_rows[: args.eval_loss_rows], args.max_length)
    log_event(log_path, event="tokenized", seconds=round(time.time() - tok_started, 1), **stats)

    steps_per_epoch = math.ceil(len(train_examples) / (args.batch_size * args.grad_accum))
    if args.mode == "dryrun":
        max_steps = 5
    elif args.mode == "speedtest":
        max_steps = args.speedtest_steps
    else:
        max_steps = args.max_steps if args.max_steps > 0 else math.ceil(steps_per_epoch * args.epochs)
    eval_steps = {"dryrun": 5, "speedtest": max_steps}.get(args.mode, args.eval_steps)
    save_steps = {"dryrun": 5, "speedtest": max_steps}.get(args.mode, args.save_steps)

    targs = TrainingArguments(
        output_dir=str(run_dir / "checkpoints"),
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.eval_batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_steps=max(1, int(max_steps * args.warmup_fraction)),
        max_steps=max_steps,
        logging_steps=1 if args.mode == "dryrun" else 10,
        eval_strategy="steps",
        eval_steps=eval_steps,
        save_strategy="steps",
        save_steps=save_steps,
        save_total_limit=3,
        bf16=torch.cuda.is_available(),
        optim="adamw_torch",
        weight_decay=0.0,
        max_grad_norm=1.0,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        dataloader_num_workers=0,
        remove_unused_columns=False,
        report_to="none",
        seed=args.seed,
        use_cpu=not torch.cuda.is_available(),
    )
    trainer = Trainer(
        model=model,
        args=targs,
        train_dataset=train_examples,
        eval_dataset=eval_examples,
        data_collator=PadCollator(tokenizer.pad_token_id),
        callbacks=make_callbacks(args, run_dir, tokenizer, val_rows),
    )
    resume = None if (args.no_resume or args.mode != "train") else latest_checkpoint(run_dir)
    if resume:
        log_event(log_path, event="resuming", checkpoint=resume)
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    train_started = time.time()
    result = trainer.train(resume_from_checkpoint=resume)
    train_seconds = time.time() - train_started
    steps_done = trainer.state.global_step - (int(Path(resume).name.split("-")[-1]) if resume else 0)

    summary: dict[str, Any] = {
        "mode": args.mode,
        "model": model_tag,
        "quantization": "none (bf16 LoRA)" if args.no_4bit else "4-bit NF4 QLoRA (double quant, bf16 compute)",
        "train_rows": len(train_examples),
        "steps_completed": trainer.state.global_step,
        "steps_planned": max_steps,
        "steps_per_epoch": steps_per_epoch,
        "train_seconds": round(train_seconds, 1),
        "seconds_per_step": round(train_seconds / max(1, steps_done), 3),
        "train_loss": round(result.training_loss, 4),
        "peak_vram_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2) if torch.cuda.is_available() else None,
        **{f"data_{k}": v for k, v in stats.items()},
    }
    if args.mode == "speedtest":
        # Account for the real (shorter-than-max) sequence lengths in the projection.
        per_step = summary["seconds_per_step"]
        summary["tokens_per_second"] = round(
            stats["mean_tokens"] * args.batch_size * args.grad_accum / max(per_step, 1e-9), 1
        )
        summary["projected_hours_per_epoch"] = round(per_step * steps_per_epoch / 3600, 2)
        for hours in (4, 5, 6, 7, 8):
            summary[f"steps_that_fit_in_{hours}h"] = int(hours * 3600 * 0.92 / per_step)
        summary["recommendation"] = (
            "Full epoch fits in 7 h: run train with --epochs 1."
            if summary["projected_hours_per_epoch"] <= 7
            else f"Full epoch does not fit; run train with --max-steps {summary['steps_that_fit_in_7h']} (or --time-budget-hours 7)."
        )

    adapter_dir = run_dir / "final_adapter"
    trainer.save_model(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))
    log_event(log_path, event="adapter_saved", path=str(adapter_dir))

    if args.mode == "dryrun":
        # Reload the saved adapter to prove the files are complete, then evaluate briefly.
        from ckit_eval import evaluate_split
        from peft import PeftModel

        del trainer, model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        base, tokenizer = load_model(args)
        reloaded = PeftModel.from_pretrained(base, str(adapter_dir))
        payload = evaluate_split(reloaded, tokenizer, val_rows[:32], run_dir / "eval" / "dryrun_validation.json",
                                 name="dryrun_validation", model_label=f"{model_tag}+dryrun-adapter",
                                 max_prompt_tokens=args.eval_max_prompt_tokens, batch_size=args.eval_batch_size)
        summary["dryrun_eval_rows"] = payload["metrics"]["overall"]["n"]
        summary["dryrun_invalid_predictions"] = payload["metrics"]["overall"]["invalid_predictions"]
        summary["status"] = "DRY RUN PASSED"
    elif args.mode == "train" and not args.skip_final_eval:
        from evaluate_qwen3 import evaluate_and_summarize

        del trainer
        summary["final_evaluation"] = evaluate_and_summarize(
            model, tokenizer, run_dir, model_label=f"{model_tag}+{run_dir.name}",
            data_dir=args.data_dir, max_prompt_tokens=args.eval_max_prompt_tokens,
            batch_size=args.eval_batch_size,
        )
    summary_name = {"dryrun": "dryrun_summary.json", "speedtest": "speedtest.json"}.get(args.mode, "train_summary.json")
    (run_dir / summary_name).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    log_event(log_path, event="done", summary_file=summary_name)
    print(json.dumps({k: v for k, v in summary.items() if k != "final_evaluation"}, indent=2))
    return summary


if __name__ == "__main__":
    run(parse_args())
