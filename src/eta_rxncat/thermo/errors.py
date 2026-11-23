"""Thermochemistry errors and the ground-state check."""

from eta_rxncat.core import ThermoResult


class ThermoError(Exception):
    """Base of every thermochemistry error."""


class ThermoInputError(ThermoError):
    """The geometry, Hessian, SMILES or option cannot be analysed (the message says why)."""


class NotAMinimumError(ThermoError):
    """A ground-state geometry has imaginary modes.

    Attributes:
        imaginary_cm1: The imaginary frequencies (cm^-1, negative), ascending.
    """

    def __init__(self, imaginary_cm1: tuple[float, ...]) -> None:
        """Record the imaginary modes and name them in the message."""
        self.imaginary_cm1 = imaginary_cm1
        listed = ", ".join(f"{f:.2f}" for f in imaginary_cm1)
        super().__init__(f"not a minimum: {len(imaginary_cm1)} imaginary mode(s) [{listed}] cm^-1")


def check_ground_state(result: ThermoResult) -> None:
    """Raise ``NotAMinimumError`` iff ``result`` lists an imaginary frequency.

    Args:
        result: The thermochemistry of a geometry expected to be a minimum.

    Raises:
        NotAMinimumError: If ``result.imaginary_frequencies_cm1`` is non-empty.
    """
    if result.imaginary_frequencies_cm1:
        raise NotAMinimumError(tuple(result.imaginary_frequencies_cm1))
