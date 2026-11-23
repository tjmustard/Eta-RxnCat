"""The typed error contract of conformer generation (mission §5 Contracts, Conformer API).

No function returns its input or a partial pool as a fallback: every failure is one of these.
"""

from collections.abc import Mapping, Sequence


class ConformerError(Exception):
    """Base of every conformer error."""


class ConformerInputError(ConformerError):
    """Unparsable SMILES, isotope label, charge or parity mismatch, or any seed failure."""


class EmbeddingFailedError(ConformerError):
    """Neither ETKDG pass produced an embedding.

    Attributes:
        counts: RDKit failure counts per pass (``pass1``, ``pass2``).
    """

    def __init__(self, counts: Mapping[str, Sequence[int]]) -> None:
        """Record the failure counts and name them in the message."""
        self.counts = {k: tuple(v) for k, v in counts.items()}
        super().__init__(f"no conformer embedded in any ETKDG pass (failure counts {self.counts})")


class EnsembleEmptyError(ConformerError):
    """Every conformer was dropped.

    Attributes:
        reasons: ``(id, reason)`` for every dropped conformer.
    """

    def __init__(self, reasons: Sequence[tuple[int, str]]) -> None:
        """Record why each conformer was dropped and name the reasons in the message."""
        self.reasons = tuple(reasons)
        super().__init__(f"every conformer was dropped: {list(self.reasons)}")
