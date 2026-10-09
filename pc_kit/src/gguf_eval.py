"""Evaluate a GGUF model through llama-server exactly the way the app calls it.

Same messages, same strict JSON-schema decoding (one of the ten valid pairs),
temperature 0. Standard library only, so it runs on the Windows PC (CUDA
llama-server from tools/) and on the Mac (Homebrew llama-server).

Examples:
  python src\\gguf_eval.py --gguf results\\qwen3-4b-main\\export\\complaintiq-qwen3-4b-Q4_K_M.gguf --limit 300
  python src/gguf_eval.py --gguf ../models/new.gguf --server-bin llama-server --split check
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "src"))

from ckit_common import PAIRS, messages_for, parse_answer  # noqa: E402
from ckit_data import read_rows  # noqa: E402
from ckit_metrics import report_by_source  # noqa: E402

RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "complaint_labels",
        "strict": True,
        "schema": {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "product": {"type": "string", "enum": [p]},
                        "issue": {"type": "string", "enum": [i]},
                    },
                    "required": ["product", "issue"],
                    "additionalProperties": False,
                }
                for p, i in PAIRS
            ]
        },
    },
}


def _post(url: str, payload: dict[str, Any], timeout: float = 120) -> dict[str, Any]:
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def classify(server: str, text: str) -> tuple[str, float]:
    started = time.perf_counter()
    data = _post(
        f"{server}/v1/chat/completions",
        {
            "messages": messages_for(text),
            "temperature": 0,
            "seed": 42,
            "max_tokens": 128,
            "response_format": RESPONSE_FORMAT,
            "stream": False,
        },
    )
    content = data["choices"][0]["message"]["content"]
    return parse_answer(content), (time.perf_counter() - started) * 1000


def find_server_binary(explicit: str | None) -> str:
    if explicit:
        return explicit
    if os.name == "nt":
        for candidate in sorted(KIT.glob("tools/llama-bin/**/llama-server.exe")):
            return str(candidate)
    found = shutil.which("llama-server")
    if found:
        return found
    raise SystemExit("llama-server not found; run setup_windows.bat or pass --server-bin")


def start_server(binary: str, gguf: Path, port: int) -> subprocess.Popen:
    process = subprocess.Popen(
        [binary, "-m", str(gguf), "-c", "2048", "-ngl", "99", "--parallel", "1",
         "--host", "127.0.0.1", "--port", str(port), "--jinja", "--reasoning", "off"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    deadline = time.time() + 300
    while time.time() < deadline:
        if process.poll() is not None:
            raise SystemExit(f"llama-server exited early with code {process.returncode}")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5) as r:
                if r.status == 200:
                    return process
        except OSError:
            pass
        time.sleep(2)
    process.terminate()
    raise SystemExit("llama-server did not become ready")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--gguf", type=Path, required=True)
    p.add_argument("--split", default="test", choices=["test", "check", "validation"])
    p.add_argument("--data-dir", type=Path, default=KIT / "data")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--server-bin", default=None)
    p.add_argument("--port", type=int, default=8604)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()
    rows = read_rows(args.data_dir / f"{args.split}.csv", args.limit or None)
    server = start_server(find_server_binary(args.server_bin), args.gguf, args.port)
    predictions = []
    try:
        for index, row in enumerate(rows):
            label, ms = classify(f"http://127.0.0.1:{args.port}", row["text"])
            predictions.append({"complaint_id": row["complaint_id"], "source": row.get("source", ""),
                                "gold": row["label"], "predicted": label, "latency_ms": round(ms, 1)})
            if (index + 1) % 50 == 0:
                print(f"  {index + 1}/{len(rows)}", flush=True)
    finally:
        server.terminate()
    report = report_by_source(rows, [x["predicted"] for x in predictions])
    out = args.out or args.gguf.parent / f"gguf_{args.split}_predictions.json"
    out.write_text(json.dumps({"model": args.gguf.name, "split": args.split, "decoding": "llama-server strict json_schema (app-identical)",
                               "latency_ms_mean": round(sum(x["latency_ms"] for x in predictions) / len(predictions), 1),
                               "metrics": report, "predictions": predictions}, indent=2), encoding="utf-8")
    overall = report["overall"]
    print(f"GGUF {args.split}: accuracy={overall['accuracy']:.4f} macro_f1={overall['macro_f1']:.4f} n={overall['n']} -> {out}")


if __name__ == "__main__":
    main()
