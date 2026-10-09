"""Write CHECKSUMS.sha256 for every file the PC needs (run on the Mac before copying).

Skips results/, .venv/ and macOS metadata.
Format: "<sha256>  <relative/path>" (two spaces, forward slashes).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {"source_data", "results", ".venv", "__pycache__", ".ipynb_checkpoints"}
SKIP_FILES = {"CHECKSUMS.sha256", ".DS_Store", ".gitignore"}


def main() -> None:
    lines = []
    for path in sorted(KIT.rglob("*")):
        relative = path.relative_to(KIT)
        if not path.is_file() or path.name in SKIP_FILES or path.name.startswith("._"):
            continue
        if any(part in SKIP_DIRS for part in relative.parts):
            continue
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1 << 20), b""):
                digest.update(block)
        lines.append(f"{digest.hexdigest()}  {relative.as_posix()}")
    (KIT / "CHECKSUMS.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(lines)} files")


if __name__ == "__main__":
    main()
