"""Merge the LoRA adapter into Qwen3-4B and export a Q4_K_M GGUF for the app.

Steps: load the bf16 base on CPU (needs ~10 GB RAM), merge the adapter, save the
merged model, convert with llama.cpp's convert_hf_to_gguf.py (from a llama.cpp checkout in tools/),
quantize with llama-quantize, write a manifest with SHA-256. Intermediate files
(merged safetensors, f16 GGUF, ~16 GB together) are deleted unless --keep-intermediate.

Example:
  python src\\export_gguf.py --adapter results\\qwen3-4b-main\\final_adapter
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def find_tool(pattern: str) -> Path:
    matches = sorted(KIT.glob(f"tools/**/{pattern}"))
    if not matches and shutil.which(pattern):  # e.g. Homebrew llama-quantize on the Mac
        return Path(shutil.which(pattern) or pattern)
    if not matches:
        raise SystemExit(f"{pattern} not found: clone llama.cpp into training/tools/ (see training/README.md).")
    return matches[0]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--adapter", type=Path, required=True)
    p.add_argument("--model-dir", type=Path, default=KIT / "model" / "Qwen3-4B-Instruct-2507")
    p.add_argument("--out-dir", type=Path, default=None, help="Default: <run folder>/export")
    p.add_argument("--name", default="complaintiq-qwen3-4b")
    p.add_argument("--quant", default="Q4_K_M", help="llama-quantize type (Q4_K_M, Q5_K_M, Q8_0)")
    p.add_argument("--keep-intermediate", action="store_true")
    p.add_argument("--verify-rows", type=int, default=0,
                   help="Then classify this many test rows through llama-server (app-identical request)")
    p.add_argument("--no-copy-to-app", action="store_true",
                   help="Do not copy the GGUF into the project's models/ folder")
    args = p.parse_args()

    run_dir = args.adapter.parent.parent if args.adapter.parent.name == "checkpoints" else args.adapter.parent
    out_dir = args.out_dir or run_dir / "export"
    out_dir.mkdir(parents=True, exist_ok=True)
    merged = out_dir / "merged_hf"
    f16 = out_dir / f"{args.name}-f16.gguf"
    final = out_dir / f"{args.name}-{args.quant}.gguf"
    started = time.time()

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print("1/3 merging adapter into the bf16 base model (CPU)...", flush=True)
    base = AutoModelForCausalLM.from_pretrained(args.model_dir, dtype=torch.bfloat16, device_map="cpu", low_cpu_mem_usage=True)
    model = PeftModel.from_pretrained(base, str(args.adapter)).merge_and_unload()
    model.save_pretrained(merged, safe_serialization=True, max_shard_size="2GB")
    AutoTokenizer.from_pretrained(args.model_dir).save_pretrained(merged)
    for extra in ("generation_config.json",):
        if (args.model_dir / extra).exists():
            shutil.copy2(args.model_dir / extra, merged / extra)
    del model, base

    print("2/3 converting to GGUF (f16)...", flush=True)
    convert = find_tool("convert_hf_to_gguf.py")
    env = {**os.environ, "PYTHONPATH": str(convert.parent / "gguf-py") + os.pathsep + os.environ.get("PYTHONPATH", "")}
    subprocess.run([sys.executable, str(convert), str(merged), "--outfile", str(f16), "--outtype", "f16"], check=True, env=env)

    print(f"3/3 quantizing to {args.quant}...", flush=True)
    quantize = find_tool("llama-quantize")
    subprocess.run([str(quantize), str(f16), str(final), args.quant], check=True)

    manifest = {
        "gguf": final.name,
        "sha256": sha256(final),
        "bytes": final.stat().st_size,
        "quantization": args.quant,
        "base_model": args.model_dir.name,
        "adapter": str(args.adapter),
        "note": "Adapter trained against the 4-bit NF4 base and merged into the bf16 base before quantization.",
        "elapsed_seconds": round(time.time() - started),
    }
    (out_dir / "export_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if not args.keep_intermediate:
        shutil.rmtree(merged, ignore_errors=True)
        f16.unlink(missing_ok=True)
    print(json.dumps(manifest, indent=2))
    app_models = KIT.parent / "models"
    if not args.no_copy_to_app and app_models.is_dir():
        shutil.copy2(final, app_models / final.name)
        print(f"Copied {final.name} to {app_models} (the app uses it automatically).")
    if args.verify_rows:
        subprocess.run([sys.executable, str(KIT / "src" / "gguf_eval.py"), "--gguf", str(final),
                        "--limit", str(args.verify_rows)], check=True)


if __name__ == "__main__":
    main()
