"""Crash-safe atomic writes for KAIRIS artifacts."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO, Iterator, TextIO


def _temporary_path(destination: Path) -> Path:
    return destination.with_name(destination.name + ".tmp")


@contextmanager
def atomic_text_writer(path: str | Path, encoding: str = "utf-8") -> Iterator[TextIO]:
    """Write text beside its destination, fsync it, then atomically replace."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_path(destination)
    try:
        with temporary.open("w", encoding=encoding, newline="") as handle:
            yield handle
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


@contextmanager
def atomic_binary_writer(path: str | Path) -> Iterator[BinaryIO]:
    """Write bytes beside their destination, fsync them, then atomically replace."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = _temporary_path(destination)
    try:
        with temporary.open("w+b") as handle:
            yield handle
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def atomic_write_text(path: str | Path, content: str, encoding: str = "utf-8") -> Path:
    destination = Path(path)
    with atomic_text_writer(destination, encoding=encoding) as handle:
        handle.write(content)
    return destination


def atomic_write_bytes(path: str | Path, content: bytes) -> Path:
    destination = Path(path)
    with atomic_binary_writer(destination) as handle:
        handle.write(content)
    return destination
