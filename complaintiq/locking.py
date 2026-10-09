"""Cross-platform, non-blocking exclusive file locks (fcntl on POSIX, msvcrt on Windows)."""

from __future__ import annotations

import sys
from typing import IO, Any

if sys.platform == "win32":
    import msvcrt

    def lock_exclusive(handle: IO[Any]) -> None:
        """Lock the first byte; raise BlockingIOError if another process holds it."""
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise BlockingIOError(str(exc)) from exc

    def unlock(handle: IO[Any]) -> None:
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)

else:
    import fcntl

    def lock_exclusive(handle: IO[Any]) -> None:
        """Raise BlockingIOError if another process holds the lock."""
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def unlock(handle: IO[Any]) -> None:
        fcntl.flock(handle, fcntl.LOCK_UN)
