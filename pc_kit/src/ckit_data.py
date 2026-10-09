"""Tokenization for training and evaluation: exact app prompt, token-budget truncation."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from ckit_common import CLASSES, PAIRS, answer_for, class_name, messages_for

IM_END = "<|im_end|>"


def read_rows(path: Path, limit: int | None = None) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return rows[:limit] if limit else rows


def prompt_text(tokenizer: Any, complaint: str) -> str:
    """Chat-template string ending with the assistant generation prompt.

    Qwen3-4B-Instruct-2507 is non-thinking only; enable_thinking=False is a no-op
    there and keeps the prompt identical to llama-server's `--reasoning off`.
    """
    return tokenizer.apply_chat_template(
        messages_for(complaint), tokenize=False, add_generation_prompt=True, enable_thinking=False
    )


def encode(tokenizer: Any, text: str) -> list[int]:
    return list(tokenizer(text, add_special_tokens=False)["input_ids"])


def answer_ids(tokenizer: Any) -> dict[str, list[int]]:
    """Token ids of each class's assistant reply including the end-of-turn token."""
    return {class_name(p, i): encode(tokenizer, answer_for(p, i) + IM_END) for p, i in PAIRS}


def fit_prompt(tokenizer: Any, complaint: str, budget: int) -> tuple[list[int], bool]:
    """Prompt ids no longer than `budget`, cutting the complaint text (not the prompt) if needed."""
    ids = encode(tokenizer, prompt_text(tokenizer, complaint))
    if len(ids) <= budget:
        return ids, False
    overhead = len(encode(tokenizer, prompt_text(tokenizer, ""))) + 2
    room = max(16, budget - overhead)
    offsets = tokenizer(complaint, add_special_tokens=False, return_offsets_mapping=True)[
        "offset_mapping"
    ]
    cut = offsets[min(room, len(offsets)) - 1][1]
    text = complaint[:cut]
    for _ in range(20):  # JSON escaping can add a few tokens; trim until it fits.
        ids = encode(tokenizer, prompt_text(tokenizer, text))
        if len(ids) <= budget:
            return ids, True
        text = text[: max(1, int(len(text) * 0.95))]
    raise ValueError("Could not fit the prompt into the token budget")


def build_training_examples(
    tokenizer: Any, rows: list[dict[str, str]], max_length: int
) -> tuple[list[dict[str, list[int]]], dict[str, Any]]:
    """input_ids/labels with the prompt masked (-100); only the answer is learned."""
    answers = answer_ids(tokenizer)
    longest_answer = max(len(v) for v in answers.values())
    examples, truncated, lengths = [], 0, []
    for row in rows:
        if row["label"] not in CLASSES:
            raise ValueError(f"Unknown label: {row['label']}")
        prompt, was_cut = fit_prompt(tokenizer, row["text"], max_length - longest_answer)
        target = answers[row["label"]]
        examples.append(
            {"input_ids": prompt + target, "labels": [-100] * len(prompt) + target}
        )
        truncated += was_cut
        lengths.append(len(prompt) + len(target))
    lengths.sort()
    stats = {
        "examples": len(examples),
        "truncated_complaints": truncated,
        "mean_tokens": round(sum(lengths) / max(1, len(lengths)), 1),
        "p50_tokens": lengths[len(lengths) // 2] if lengths else 0,
        "max_tokens": lengths[-1] if lengths else 0,
        "total_tokens": sum(lengths),
    }
    return examples, stats


class PadCollator:
    """Right-pad a batch for training."""

    def __init__(self, pad_id: int) -> None:
        self.pad_id = pad_id

    def __call__(self, batch: list[dict[str, list[int]]]) -> dict[str, Any]:
        import torch

        width = max(len(item["input_ids"]) for item in batch)
        ids, labels, mask = [], [], []
        for item in batch:
            gap = width - len(item["input_ids"])
            ids.append(item["input_ids"] + [self.pad_id] * gap)
            labels.append(item["labels"] + [-100] * gap)
            mask.append([1] * len(item["input_ids"]) + [0] * gap)
        return {
            "input_ids": torch.tensor(ids),
            "labels": torch.tensor(labels),
            "attention_mask": torch.tensor(mask),
        }
