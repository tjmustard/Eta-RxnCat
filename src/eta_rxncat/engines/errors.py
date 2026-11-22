"""The typed error contract shared by every engine (mission §5 Contracts, Errors).

``EngineError`` is the base. Engines raise exactly one of the four subclasses, catch library
exceptions by named type and re-raise ``from`` the cause, and never return a partial result.
"""

import re

TAIL_MAX_LINES = 40
"""The most lines an ``EngineRuntimeError`` diagnostic tail keeps."""

_SECRET = re.compile(r"\bhf_[A-Za-z0-9]{16,}\b|(?i:\b(?:bearer|token)[ =:]+)\S+")


def redact(text: str) -> str:
    """Return ``text`` with Hugging Face tokens and ``token=``/``Bearer`` values replaced."""
    return _SECRET.sub("<redacted>", text)


class EngineError(Exception):
    """Base of every engine error."""


class EngineUnavailableError(EngineError):
    """A missing extra, binary, model weights or GPU; the message names the install step."""


class EngineInputError(EngineError):
    """The state, stage or option cannot be represented by this engine."""


class ScfConvergenceError(EngineError):
    """The SCF did not converge; ``steps`` records every recovery step tried, in order."""

    def __init__(self, message: str, steps: tuple[str, ...] = ()) -> None:
        """Store the message and the steps tried."""
        super().__init__(message)
        self.steps: tuple[str, ...] = tuple(steps)


class EngineRuntimeError(EngineError):
    """A library or subprocess failure, with a redacted diagnostic tail of <= 40 lines."""

    def __init__(self, message: str, tail: str = "") -> None:
        """Store the message and the last ``TAIL_MAX_LINES`` lines of ``tail``, redacted."""
        super().__init__(message)
        self.tail: str = redact("\n".join(tail.splitlines()[-TAIL_MAX_LINES:]))
