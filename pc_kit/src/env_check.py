"""Check the Windows training environment before spending GPU time.

Exit code 0 = ready. Checks: Python/torch versions, CUDA + GPU + bf16, a real
bitsandbytes 4-bit forward/backward on the GPU, model files, tokenizer, data
files, free disk, and the llama.cpp tools used for GGUF export.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("BITSANDBYTES_NOWELCOME", "1")
MODEL = KIT / "model" / "Qwen3-4B-Instruct-2507"

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    results.append((name, ok, detail))
    print(f"[{'OK' if ok else 'FAIL'}] {name}{': ' + detail if detail else ''}", flush=True)
    return ok


def main() -> int:
    check("Python 3.11", sys.version_info[:2] == (3, 11), platform.python_version())
    try:
        import torch

        check("torch", True, f"{torch.__version__} (CUDA build {torch.version.cuda})")
        cuda = torch.cuda.is_available()
        check("CUDA available", cuda, torch.cuda.get_device_name(0) if cuda else "no GPU visible to torch")
        if cuda:
            props = torch.cuda.get_device_properties(0)
            check("GPU memory >= 11 GB", props.total_memory / 2**30 >= 11, f"{props.total_memory / 2**30:.1f} GB")
            check("bf16 supported", torch.cuda.is_bf16_supported())
            x = torch.randn(1024, 1024, device="cuda", dtype=torch.bfloat16)
            check("GPU matmul", bool(torch.isfinite(x @ x).all()))
    except Exception as error:  # noqa: BLE001
        check("torch import", False, repr(error))
        cuda = False

    if cuda:
        try:
            import bitsandbytes as bnb
            import torch

            layer = bnb.nn.Linear4bit(256, 256, compute_dtype=torch.bfloat16, quant_type="nf4").cuda()
            inp = torch.randn(4, 256, device="cuda", dtype=torch.bfloat16, requires_grad=True)
            layer(inp).float().sum().backward()
            check("bitsandbytes 4-bit forward/backward", inp.grad is not None, bnb.__version__)
        except Exception as error:  # noqa: BLE001
            check("bitsandbytes 4-bit forward/backward", False, repr(error)[:300])

    for package in ("transformers", "peft", "accelerate"):
        try:
            module = __import__(package)
            check(package, True, module.__version__)
        except Exception as error:  # noqa: BLE001
            check(package, False, repr(error))

    index = MODEL / "model.safetensors.index.json"
    if check("model index", index.exists(), str(index)):
        shards = sorted(set(json.loads(index.read_text())["weight_map"].values()))
        missing = [s for s in shards if not (MODEL / s).exists()]
        check("model shards present", not missing, ", ".join(missing) or f"{len(shards)} shards")
    try:
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(MODEL)
        check("tokenizer loads offline", True, f"vocab {len(tokenizer)}")
    except Exception as error:  # noqa: BLE001
        check("tokenizer loads offline", False, repr(error)[:300])

    for name in ("train", "validation", "test", "check"):
        path = KIT / "data" / f"{name}.csv"
        if path.exists():
            with path.open(encoding="utf-8") as handle:
                rows = sum(1 for _ in handle) - 1
            check(f"data/{name}.csv", rows > 0, f"~{rows} lines")
        else:
            check(f"data/{name}.csv", False, "missing")

    free = shutil.disk_usage(KIT).free / 2**30
    check("free disk >= 30 GB", free >= 30, f"{free:.0f} GB free on the kit drive")

    servers = sorted(KIT.glob("tools/llama-bin/**/llama-server.exe"))
    if servers and os.name == "nt":
        try:
            out = subprocess.run([str(servers[0]), "--version"], capture_output=True, text=True, timeout=60)
            check("llama-server.exe runs", out.returncode == 0, (out.stdout + out.stderr).strip().splitlines()[-1][:120])
        except Exception as error:  # noqa: BLE001
            check("llama-server.exe runs", False, repr(error))
    else:
        check("llama.cpp tools present", bool(servers), "tools/llama-bin")

    failed = [name for name, ok, _ in results if not ok]
    print("\nREADY" if not failed else f"\nNOT READY: {', '.join(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
