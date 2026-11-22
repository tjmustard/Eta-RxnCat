"""Content-pinned model identity and library versions (mission R5, ADR-0017 PROPOSED)."""

import hashlib
import importlib.metadata as md
from pathlib import Path

from eta_rxncat.engines.errors import EngineUnavailableError

CHUNK_BYTES = 1 << 20
"""Read size for hashing model files (1 MiB)."""


def sha256_file(path: Path) -> str:
    """Return the sha256 hex digest of ``path``, streamed in 1 MiB chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def model_id(name: str, path: Path) -> str:
    """Return ``"<name>@sha256:<64 hex>"`` for model weights at ``path``; never the path itself."""
    return f"{name}@sha256:{sha256_file(path)}"


def library_version(dist: str) -> str:
    """Return the installed version of distribution ``dist``.

    Raises:
        EngineUnavailableError: ``dist`` is not installed.
    """
    try:
        return md.version(dist)
    except md.PackageNotFoundError as exc:
        raise EngineUnavailableError(
            f"distribution {dist!r} is not installed; install the engine's extra "
            "(uv sync --extra <extra>)"
        ) from exc
