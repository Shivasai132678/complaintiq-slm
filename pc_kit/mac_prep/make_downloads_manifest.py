"""Write downloads.json: everything the PC can fetch from the internet instead of copying.

Each entry: url, dest (relative to pc_kit), sha256, bytes, and optional "extract_to"
(zip unpacked after download) / "when" ("driver_needed" = fetched only if the driver is missing).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
HF = "https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/resolve/cdbee75f17c01a7cc42f958dc650907174af0554/"
LLAMA = "https://github.com/ggml-org/llama.cpp/releases/download/b11496/"
MODEL_FILES = [
    "LICENSE", "README.md", "config.json", "generation_config.json", "merges.txt",
    "model.safetensors.index.json", "tokenizer.json", "tokenizer_config.json", "vocab.json",
    "model-00001-of-00003.safetensors", "model-00002-of-00003.safetensors",
    "model-00003-of-00003.safetensors",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def entry(url: str, dest: str, **extra: object) -> dict[str, object]:
    path = KIT / dest
    return {"url": url, "dest": dest, "sha256": sha256(path), "bytes": path.stat().st_size, **extra}


def main() -> None:
    items = [
        entry("https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe", "installers/python-3.11.9-amd64.exe"),
        entry("https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe", "installers/python-3.12.10-amd64.exe"),
        entry("https://aka.ms/vs/17/release/vc_redist.x64.exe", "installers/vc_redist.x64.exe", verify=False),
        entry("https://github.com/git-for-windows/git/releases/download/v2.56.0.windows.2/Git-2.56.0.2-64-bit.exe", "installers/Git-2.56.0.2-64-bit.exe", optional=True),
        entry("https://us.download.nvidia.com/Windows/617.42/617.42-desktop-win10-win11-64bit-international-dch-whql.exe",
              "installers/nvidia-617.42-desktop-win10-win11-64bit-international-dch-whql.exe", when="driver_needed"),
    ]
    items += [entry(HF + name, f"model/Qwen3-4B-Instruct-2507/{name}") for name in MODEL_FILES]
    items += [
        {"url": LLAMA + "llama-b11496-bin-win-cuda-12.4-x64.zip", "dest": "downloads/llama-b11496-bin-win-cuda-12.4-x64.zip",
         "sha256": "b0f1c8c8ff9e19282b99d360a17e50c0ed27461e569b74cb88c6672fe814fe9b", "bytes": 264908642,
         "extract_to": "tools/llama-bin", "skip_if_exists": "tools/llama-bin/llama-server.exe"},
        {"url": LLAMA + "cudart-llama-bin-win-cuda-12.4-x64.zip", "dest": "downloads/cudart-llama-bin-win-cuda-12.4-x64.zip",
         "sha256": "8c79a9b226de4b3cacfd1f83d24f962d0773be79f1e7b75c6af4ded7e32ae1d6", "bytes": 391443627,
         "extract_to": "tools/llama-bin", "skip_if_exists": "tools/llama-bin/cudart64_12.dll"},
    ]
    (KIT / "downloads.json").write_text(json.dumps({"items": items}, indent=2), encoding="utf-8")
    print(len(items), "entries", round(sum(int(i["bytes"]) for i in items) / 2**30, 2), "GB")


if __name__ == "__main__":
    main()
