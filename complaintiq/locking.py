"""Non-blocking exclusive file locks (POSIX flock)."""

from __future__ import annotations

import fcntl
from typing import IO, Any


def lock_exclusive(handle: IO[Any]) -> None:
    """Raise BlockingIOError if another process holds the lock."""
    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)


def unlock(handle: IO[Any]) -> None:
    fcntl.flock(handle, fcntl.LOCK_UN)
