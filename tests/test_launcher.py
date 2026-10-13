"""Launcher model/server selection and the database worker lock."""

from __future__ import annotations

from pathlib import Path

import pytest

import scripts.launch_pilot as launcher
from complaintiq.locking import lock_exclusive, unlock


def test_second_lock_on_same_file_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "db.worker.lock"
    with path.open("a+") as first, path.open("a+") as second:
        lock_exclusive(first)
        with pytest.raises(BlockingIOError):
            lock_exclusive(second)
        unlock(first)
        lock_exclusive(second)
        unlock(second)


def test_model_and_server_selection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    model, other = tmp_path / "model.gguf", tmp_path / "other.gguf"
    monkeypatch.setattr(launcher, "NEW_MODEL", model)
    monkeypatch.delenv("COMPLAINTIQ_MODEL_PATH", raising=False)
    assert launcher.default_model() == model.resolve()
    monkeypatch.setenv("COMPLAINTIQ_MODEL_PATH", str(other))
    assert launcher.default_model() == other.resolve()

    binary = tmp_path / "llama-server"
    binary.write_bytes(b"")
    monkeypatch.setenv("COMPLAINTIQ_LLAMA_SERVER", str(binary))
    assert launcher.find_llama_server() == str(binary)
