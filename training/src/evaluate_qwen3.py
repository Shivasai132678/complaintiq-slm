"""Evaluate a trained adapter (or the untuned base model) on the test and check sets.

Writes per-row predictions plus eval/results.md and eval/results.json (accuracy,
macro precision/recall/F1, product accuracy, out-of-scope precision/recall).

Examples:
  python src\\evaluate_qwen3.py --adapter results\\qwen3-4b-main\\final_adapter
  python src\\evaluate_qwen3.py --adapter results\\qwen3-4b-main\\checkpoints\\checkpoint-2000
  python src\\evaluate_qwen3.py --base-only --limit 500     (zero-shot Qwen3, optional)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "src"))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from ckit_data import read_rows  # noqa: E402
from ckit_metrics import load_predictions, report_by_source, summary_markdown  # noqa: E402


def summarize(run_eval_dir: Path, label: str, data_dir: Path) -> dict[str, Any]:
    """Write results.md / results.json from the saved test and check predictions."""
    out: dict[str, Any] = {"model": label}
    markdown = [f"# Results: {label}", ""]
    titles = {"test": "Test set (newest months, Feb-Jul 2026, 10 classes)", "check": "Held-out check set"}
    for split in ("test", "check"):
        saved = run_eval_dir / f"{split}_predictions.json"
        if not saved.exists():
            continue
        predicted = load_predictions(saved)
        rows = [r for r in read_rows(data_dir / f"{split}.csv") if r["complaint_id"] in predicted]
        report = report_by_source(rows, [predicted[r["complaint_id"]] for r in rows])
        out[split] = report
        markdown.append(summary_markdown(report, f"{titles[split]}: {len(rows)} rows"))
    (run_eval_dir / "results.md").write_text("\n".join(markdown), encoding="utf-8")
    (run_eval_dir / "results.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\n".join(markdown))
    return out


def evaluate_and_summarize(
    model: Any,
    tokenizer: Any,
    run_dir: Path,
    *,
    model_label: str,
    data_dir: Path,
    max_prompt_tokens: int,
    batch_size: int,
    limit: int = 0,
) -> dict[str, Any]:
    from ckit_eval import evaluate_split

    eval_dir = run_dir / "eval"
    summary: dict[str, Any] = {}
    for split in ("test", "check"):
        rows = read_rows(data_dir / f"{split}.csv", limit or None)
        payload = evaluate_split(
            model, tokenizer, rows, eval_dir / f"{split}_predictions.json",
            name=split, model_label=model_label, max_prompt_tokens=max_prompt_tokens,
            batch_size=batch_size,
        )
        summary[split] = payload["metrics"]["overall"]
    summarize(eval_dir, model_label, data_dir)
    return summary


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--adapter", type=Path, help="final_adapter or checkpoint-N folder")
    p.add_argument("--base-only", action="store_true", help="Evaluate the untuned base model")
    p.add_argument("--model-dir", type=Path, default=KIT / "model" / "Qwen3-4B-Instruct-2507")
    p.add_argument("--data-dir", type=Path, default=KIT / "data")
    p.add_argument("--out", type=Path, help="Run folder for eval/ output (default: adapter's run folder)")
    p.add_argument("--no-4bit", action="store_true")
    p.add_argument("--eval-max-prompt-tokens", type=int, default=1024)
    p.add_argument("--eval-batch-size", type=int, default=16)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--summary-only", action="store_true", help="Rebuild results.md from saved predictions")
    p.add_argument("--allow-cpu", action="store_true", help=argparse.SUPPRESS)
    args = p.parse_args()
    if not args.adapter and not args.base_only:
        p.error("pass --adapter PATH or --base-only")
    if args.out:
        run_dir = args.out
    elif args.adapter:
        run_dir = args.adapter.parent.parent if args.adapter.parent.name == "checkpoints" else args.adapter.parent
        if args.adapter.parent.name == "checkpoints":
            run_dir = run_dir / f"eval_{args.adapter.name}"
    else:
        run_dir = KIT / "results" / f"zero-shot-{args.model_dir.name}"
    label = f"{args.model_dir.name}+{args.adapter.name if args.adapter else 'zero-shot'}"
    if args.summary_only:
        summarize(run_dir / "eval", label, args.data_dir)
        return

    from train_qwen3 import load_model

    load_args = argparse.Namespace(model_dir=args.model_dir, no_4bit=args.no_4bit, allow_cpu=args.allow_cpu)
    model, tokenizer = load_model(load_args)
    if args.adapter:
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, str(args.adapter))
    evaluate_and_summarize(
        model, tokenizer, run_dir, model_label=label, data_dir=args.data_dir,
        max_prompt_tokens=args.eval_max_prompt_tokens, batch_size=args.eval_batch_size, limit=args.limit,
    )


if __name__ == "__main__":
    main()
