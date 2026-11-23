"""The typed error contract of every optimizer (mission §5 Contracts, Optimizer interface).

None of these subclasses ``ValueError``: a check inside a pydantic validator that raises one of
them propagates unchanged instead of being folded into a ``ValidationError``.
"""


class OptimizerError(Exception):
    """Base of every optimizer error."""


class OptimizerUnavailableError(OptimizerError):
    """The optimizer library is not installed; the message names the install step."""


class OptimizerInputError(OptimizerError):
    """An unknown or mistyped option, a bad constraint, or an empty or mismatched state."""


class OptimizationFailedError(OptimizerError):
    """Every recovery step failed, or a converged run broke a constraint.

    Attributes:
        steps: The recovery steps tried, in order.
        last_energy_hartree: The last energy seen (Eh), if any evaluation completed.
    """

    def __init__(
        self, message: str, *, steps: tuple[str, ...], last_energy_hartree: float | None
    ) -> None:
        """Record the steps and the last energy, and name them in the message."""
        self.steps = steps
        self.last_energy_hartree = last_energy_hartree
        super().__init__(f"{message} (steps {list(steps)}, last energy {last_energy_hartree})")
