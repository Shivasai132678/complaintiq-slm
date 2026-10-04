"""GPU-only Unsloth QLoRA training for the ComplaintIQ classifier. Run on Colab/Kaggle, never on the Mac.

Trains Qwen2.5-1.5B-Instruct on the chat-formatted examples in ``data/finetuning/training.jsonl``
(the same file uploaded to Unsloth for the delivered checkpoint), saves the LoRA adapter, and can
export a Q4_K_M GGUF for local llama.cpp inference. Install Unsloth with its official cells first.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

BASE_MODEL = "unsloth/Qwen2.5-1.5B-Instruct"


def read_jsonl(path: Path) -> list[dict]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/finetuning"))
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Persistent Drive path on Colab, /kaggle/working on Kaggle",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=2,
        help="Optimizer steps. Run a 2-step smoke test first; use -1 for full --epochs training.",
    )
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--max-length", type=int, default=2048)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--export-gguf", action="store_true", help="Also export Q4_K_M GGUF")
    args = parser.parse_args()
    # Import Unsloth before Transformers/TRL so its runtime patches apply.
    from unsloth import FastLanguageModel  # isort: skip

    import torch
    from datasets import Dataset
    from transformers.trainer_utils import get_last_checkpoint
    from trl import SFTConfig, SFTTrainer

    if not torch.cuda.is_available():
        raise RuntimeError("Select a free GPU runtime before continuing. No local Mac training.")

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=BASE_MODEL, max_seq_length=args.max_length, load_in_4bit=True
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        lora_alpha=16,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
    )

    def to_dataset(name: str) -> Dataset:
        # Each line already holds the system prompt, the clipped complaint and the labelled answer.
        rows = read_jsonl(args.data / f"{name}.jsonl")
        texts = [
            tokenizer.apply_chat_template(
                r["messages"], tokenize=False, add_generation_prompt=False
            )
            for r in rows
        ]
        return Dataset.from_list([{"text": t} for t in texts])

    args.output.mkdir(parents=True, exist_ok=True)
    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=to_dataset("training"),
        eval_dataset=to_dataset("validation"),
        args=SFTConfig(
            output_dir=str(args.output),
            dataset_text_field="text",
            max_length=args.max_length,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=8,
            warmup_steps=10,
            max_steps=args.steps,
            num_train_epochs=args.epochs,
            learning_rate=2e-4,
            logging_steps=10,
            save_steps=100,
            save_total_limit=3,
            eval_strategy="steps",
            eval_steps=100,
            optim="adamw_8bit",
            weight_decay=0.01,
            lr_scheduler_type="linear",
            seed=42,
            report_to="none",
        ),
    )
    resume = get_last_checkpoint(str(args.output)) if args.resume else None
    stats = trainer.train(resume_from_checkpoint=resume)
    model.save_pretrained(str(args.output / "adapter"))
    tokenizer.save_pretrained(str(args.output / "adapter"))
    (args.output / "run_status.json").write_text(
        json.dumps(
            {
                "base_model": BASE_MODEL,
                "training_kind": "QLoRA (4-bit base, LoRA r=16)",
                "training_file": str(args.data / "training.jsonl"),
                "global_steps": trainer.state.global_step,
                "train_loss": stats.training_loss,
                "log_history": trainer.state.log_history,
                "smoke_only": 0 < args.steps <= 2,
            },
            indent=2,
        )
    )
    if args.export_gguf:
        model.save_pretrained_gguf(
            str(args.output / "gguf"), tokenizer, quantization_method="q4_k_m"
        )
    print("Adapter saved. Evaluate the exported GGUF locally before making quality claims.")


if __name__ == "__main__":
    main()
