"""Constrained-decoding evaluation of a (PEFT) causal LM on a labelled CSV.

Decoding is restricted to the ten valid replies with a token trie, which mirrors
the app's strict JSON-schema decoding in llama.cpp. Writes per-row predictions
and a metrics report.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from ckit_data import answer_ids, fit_prompt
from ckit_metrics import report_by_source


class AnswerTrie:
    def __init__(self, answers: dict[str, list[int]], end_id: int) -> None:
        self.answers = answers
        self.end_id = end_id
        self.root: dict[int, Any] = {}
        for label, ids in answers.items():
            node = self.root
            for token in ids:
                node = node.setdefault(token, {})
            node["label"] = label
        self.max_len = max(len(v) for v in answers.values())

    def allowed(self, generated: list[int]) -> list[int]:
        node = self.root
        for token in generated:
            if token not in node:
                return [self.end_id]
            node = node[token]
        options = [t for t in node if t != "label"]
        return options or [self.end_id]

    def label(self, generated: list[int]) -> str:
        node = self.root
        for token in generated:
            if token not in node:
                return "invalid"
            node = node[token]
            if "label" in node:
                return str(node["label"])
        return "invalid"


def predict(
    model: Any,
    tokenizer: Any,
    rows: list[dict[str, str]],
    *,
    max_prompt_tokens: int,
    batch_size: int = 16,
    progress: bool = True,
) -> list[dict[str, Any]]:
    import torch

    answers = answer_ids(tokenizer)
    end_id = tokenizer.convert_tokens_to_ids("<|im_end|>")
    pad_id = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else end_id
    trie = AnswerTrie(answers, end_id)
    device = next(model.parameters()).device
    was_training = model.training
    model.eval()
    results: list[dict[str, Any]] = []
    order = sorted(range(len(rows)), key=lambda i: len(rows[i]["text"]))  # less padding
    prompts = {}
    for i in order:
        prompts[i] = fit_prompt(tokenizer, rows[i]["text"], max_prompt_tokens)
    started = time.perf_counter()
    for start in range(0, len(order), batch_size):
        chunk = order[start : start + batch_size]
        width = max(len(prompts[i][0]) for i in chunk)
        ids = [[pad_id] * (width - len(prompts[i][0])) + prompts[i][0] for i in chunk]
        mask = [[0] * (width - len(prompts[i][0])) + [1] * len(prompts[i][0]) for i in chunk]
        input_ids = torch.tensor(ids, device=device)
        attention = torch.tensor(mask, device=device)

        def allowed(batch_id: int, sequence: Any) -> list[int]:
            return trie.allowed(sequence[width:].tolist())

        batch_started = time.perf_counter()
        with torch.no_grad():
            output = model.generate(
                input_ids=input_ids,
                attention_mask=attention,
                max_new_tokens=trie.max_len + 1,
                do_sample=False,
                prefix_allowed_tokens_fn=allowed,
                eos_token_id=end_id,
                pad_token_id=pad_id,
                use_cache=True,
            )
        per_row_ms = (time.perf_counter() - batch_started) * 1000 / len(chunk)
        for row_index, sequence in zip(chunk, output):
            generated = sequence[width:].tolist()
            row = rows[row_index]
            results.append(
                {
                    "index": row_index,
                    "complaint_id": row["complaint_id"],
                    "source": row.get("source", ""),
                    "gold": row["label"],
                    "predicted": trie.label(generated),
                    "prompt_truncated": prompts[row_index][1],
                    "latency_ms_batched": round(per_row_ms, 1),
                }
            )
        if progress and (start // batch_size) % 10 == 0:
            done = min(start + batch_size, len(order))
            rate = done / (time.perf_counter() - started)
            print(f"  evaluated {done}/{len(order)} ({rate:.1f} rows/s)", flush=True)
    if was_training:
        model.train()
    results.sort(key=lambda r: r["index"])
    return results


def evaluate_split(
    model: Any,
    tokenizer: Any,
    rows: list[dict[str, str]],
    output: Path,
    *,
    name: str,
    model_label: str,
    max_prompt_tokens: int,
    batch_size: int,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started = time.time()
    predictions = predict(
        model, tokenizer, rows, max_prompt_tokens=max_prompt_tokens, batch_size=batch_size
    )
    report = report_by_source(rows, [p["predicted"] for p in predictions])
    payload = {
        "model": model_label,
        "split": name,
        "decoding": "greedy, constrained to the 10 valid replies (token trie)",
        "max_prompt_tokens": max_prompt_tokens,
        "elapsed_seconds": round(time.time() - started, 1),
        **(extra or {}),
        "metrics": report,
        "predictions": predictions,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    overall = report["overall"]
    print(
        f"[{name}] accuracy={overall['accuracy']:.4f} macro_f1={overall['macro_f1']:.4f} "
        f"in_scope_joint={overall['in_scope_joint_accuracy']} -> {output}",
        flush=True,
    )
    return payload
