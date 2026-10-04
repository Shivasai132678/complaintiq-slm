"""Start the local model and app, reusing only compatible local services."""

from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import TextIO
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
HTTP = build_opener(ProxyHandler({}))


def get(url):
    with HTTP.open(url, timeout=3) as response:
        return json.load(response)


def occupied(port):
    with socket.socket() as sock:
        return sock.connect_ex(("127.0.0.1", port)) == 0


def wait(url, child, seconds=90):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if child.poll() is not None:
            raise RuntimeError("A service exited. See logs in data/logs.")
        try:
            return get(url)
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("Service readiness timed out. See logs in data/logs.")


def main():
    model = Path(
        os.environ.get(
            "COMPLAINTIQ_MODEL_PATH", str(ROOT / "models/Qwen2.5-1.5B-Instruct.Q4_K_M.gguf")
        )
    ).resolve()
    server = shutil.which("llama-server") or "/opt/homebrew/bin/llama-server"
    if not model.is_file() or not Path(server).is_file():
        raise RuntimeError("Install llama.cpp and place the GGUF in models; see README.")
    if not (ROOT / "frontend/dist/index.html").is_file():
        raise RuntimeError("Build the frontend first: cd frontend && npm ci && npm run build")
    children: list[subprocess.Popen] = []
    logs: list[TextIO] = []

    def shutdown(*args):
        for child in reversed(children):
            child.terminate()
        for child in reversed(children):
            try:
                child.wait(timeout=135)
            except subprocess.TimeoutExpired:
                child.kill()
        for log in logs:
            log.close()

    signal.signal(signal.SIGTERM, lambda *args: sys.exit(0))
    signal.signal(signal.SIGINT, lambda *args: sys.exit(0))
    try:
        folder = ROOT / "data/logs"
        folder.mkdir(exist_ok=True)
        if occupied(8504):
            ids = [v["id"] for v in get("http://127.0.0.1:8504/v1/models")["data"]]
            if str(model) not in ids:
                raise RuntimeError(
                    "Port 8504 is serving a different model. Stop it explicitly before starting this pilot."
                )
            get("http://127.0.0.1:8504/health")
            print("Reusing the matching local model server.", flush=True)
        else:
            log = (folder / "model.log").open("a")
            logs.append(log)
            child = subprocess.Popen(
                [
                    server,
                    "-m",
                    str(model),
                    "-c",
                    "2048",
                    "-ngl",
                    "99",
                    "-t",
                    "4",
                    "-b",
                    "256",
                    "-ub",
                    "128",
                    "--parallel",
                    "1",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8504",
                    "--jinja",
                    "--reasoning",
                    "off",
                ],
                cwd=ROOT,
                stdout=log,
                stderr=log,
            )
            children.append(child)
            wait("http://127.0.0.1:8504/health", child)
        if occupied(8501):
            health = get("http://127.0.0.1:8501/api/health")
            system = get("http://127.0.0.1:8501/api/system")
            if health.get("model_version") != model.name or system.get("schema_version") != 1:
                raise RuntimeError("Port 8501 is occupied by a different app or configuration.")
            print("Compatible pilot already running: http://127.0.0.1:8501", flush=True)
            # Do not stop a model just started for an existing app; remain as its supervisor.
        else:
            env = {
                **os.environ,
                "COMPLAINTIQ_BACKEND": "slm",
                "COMPLAINTIQ_MODEL_PATH": str(model),
                "COMPLAINTIQ_MODEL_URL": "http://127.0.0.1:8504",
                "COMPLAINTIQ_EVALUATION_PATH": str(ROOT / "artifacts/finetuned_evaluation.json"),
            }
            log = (folder / "app.log").open("a")
            logs.append(log)
            child = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "complaintiq.api:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8501",
                    "--no-access-log",
                ],
                cwd=ROOT,
                env=env,
                stdout=log,
                stderr=log,
            )
            children.append(child)
            wait("http://127.0.0.1:8501/api/health", child)
            print(
                "ComplaintIQ is ready: http://127.0.0.1:8501\nKeep this terminal open. Ctrl+C stops services started here.",
                flush=True,
            )
        while children:
            if any(child.poll() is not None for child in children):
                raise RuntimeError("A service stopped. Inspect data/logs and restart the launcher.")
            time.sleep(1)
    finally:
        shutdown()


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
