"""Errors of the conserved-core mapper."""


class MappingError(Exception):
    """Base of every mapping error."""


class AlignmentError(MappingError):
    """A pair set cannot be superposed uniquely (too few, degenerate or malformed points)."""


class GraftInputError(MappingError):
    """A graft request does not fit its input structures (the message says why)."""


class GraftClashError(MappingError):
    """Two product atoms are closer than the overlap floor.

    Attributes:
        i: Lower product index of the pair.
        j: Higher product index of the pair.
        distance_angstrom: Their distance.
    """

    def __init__(self, i: int, j: int, distance_angstrom: float) -> None:
        """Record the clashing pair and name it in the message."""
        self.i = i
        self.j = j
        self.distance_angstrom = distance_angstrom
        super().__init__(
            f"product atoms {i} and {j} overlap: {distance_angstrom:.6f} angstrom apart"
        )


class CoreDisplacementError(MappingError):
    """A constrained-core atom moved during pre-relaxation.

    Attributes:
        atom: Product index of the core atom that moved most.
        displacement_angstrom: Its displacement from the input position.
    """

    def __init__(self, atom: int, displacement_angstrom: float) -> None:
        """Record the moved core atom and name it in the message."""
        self.atom = atom
        self.displacement_angstrom = displacement_angstrom
        super().__init__(f"constrained core atom {atom} moved {displacement_angstrom:.3e} angstrom")
