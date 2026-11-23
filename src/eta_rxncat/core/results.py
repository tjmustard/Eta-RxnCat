"""The ``PotentialResult`` contract every engine returns (v0.2.0).

Data only: plain lists, no numpy and no engine imports. Engines convert, symmetrise and fill it;
the model validates shapes, symmetry, finiteness and field pairing, and never changes the data.
"""

from typing import Annotated, Literal, Self

from pydantic import Field, FiniteFloat, model_validator

from eta_rxncat.core.models import CoreModel, EngineIdentity, PositiveInt

NonNegativeFiniteFloat = Annotated[float, Field(ge=0, allow_inf_nan=False)]

HessianMethod = Literal["analytic", "finite_difference"]
"""How the Hessian was obtained."""

Device = Literal["cpu", "cuda"]
"""Where the evaluation ran."""


class PotentialResult(CoreModel):
    """One engine evaluation of a ``MolecularState``, in atomic units.

    Units and conventions (mission §5 Contracts, R15):

    - Energy in Hartree (Eh).
    - Forces are ``-dE/dx`` in Hartree/Bohr, one ``[fx, fy, fz]`` row per atom (N x 3), in the
      state's atom order. They are forces, not gradients: the sign is the negative gradient.
    - The Hessian is the Cartesian second derivative ``d2E/dx_i dx_j`` in Hartree/Bohr^2, 3N x 3N,
      indexed ``3 * atom + axis`` (axis x, y, z = 0, 1, 2). It is not mass-weighted and not
      projected (translations and rotations are left in). It must be exactly symmetric
      (``H[i][j] == H[j][i]``): the engine symmetrises it and records the largest
      pre-symmetrisation ``|H[i][j] - H[j][i]|`` in ``hessian_max_asymmetry`` (Eh/Bohr^2).
    - Wall time in seconds.

    Consumers (DV-23): the model is frozen only shallowly; its force and Hessian lists are
    ordinary mutable lists. A consumer that needs a matrix to transform copies it first (for
    example ``numpy.array(result.hessian_hartree_per_bohr2)``) and never mutates the lists in
    place.

    Attributes:
        energy_hartree: Total electronic energy (Eh).
        forces_hartree_per_bohr: Forces (Eh/Bohr), N x 3, or ``None`` if not computed.
        hessian_hartree_per_bohr2: Cartesian Hessian (Eh/Bohr^2), 3N x 3N, exactly symmetric,
            or ``None`` if not computed.
        hessian_method: ``analytic`` or ``finite_difference``; set iff the Hessian is set.
        hessian_max_asymmetry: Largest asymmetry removed by symmetrisation (>= 0); set iff the
            Hessian is set.
        engine: The engine tag, version and model weights that produced the result.
        stage_engine_impl: The engine implementation version of the stage (>= 1).
        device: ``cpu`` or ``cuda``.
        device_reason: Why that device was used (for example a fallback), if recorded.
        wall_time_s: Wall-clock time of the evaluation (>= 0 s).
        recovery_steps: SCF or engine recovery steps taken, in order (empty if none).
    """

    energy_hartree: FiniteFloat
    forces_hartree_per_bohr: list[list[FiniteFloat]] | None = None
    hessian_hartree_per_bohr2: list[list[FiniteFloat]] | None = None
    hessian_method: HessianMethod | None = None
    hessian_max_asymmetry: NonNegativeFiniteFloat | None = None
    engine: EngineIdentity
    stage_engine_impl: PositiveInt
    device: Device
    device_reason: Annotated[str, Field(min_length=1)] | None = None
    wall_time_s: NonNegativeFiniteFloat
    recovery_steps: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_shapes(self) -> Self:
        forces = self.forces_hartree_per_bohr
        if forces is not None:
            if not forces:
                raise ValueError("forces_hartree_per_bohr must have at least one row")
            bad = [i for i, row in enumerate(forces) if len(row) != 3]
            if bad:
                raise ValueError(f"forces_hartree_per_bohr rows {bad} do not have length 3")
        hessian = self.hessian_hartree_per_bohr2
        if hessian is not None:
            side = len(hessian)
            if side == 0 or side % 3:
                raise ValueError(
                    f"hessian_hartree_per_bohr2 side {side} is not a positive multiple of 3"
                )
            bad = [i for i, row in enumerate(hessian) if len(row) != side]
            if bad:
                raise ValueError(f"hessian_hartree_per_bohr2 is not square: rows {bad}")
            if forces is not None and side != 3 * len(forces):
                raise ValueError(
                    f"hessian_hartree_per_bohr2 side {side} != 3 x {len(forces)} force rows"
                )
            for i in range(side):
                for j in range(i + 1, side):
                    if hessian[i][j] != hessian[j][i]:
                        raise ValueError(
                            f"hessian_hartree_per_bohr2 is not exactly symmetric at [{i}][{j}]"
                        )
        has_hessian = hessian is not None
        for name in ("hessian_method", "hessian_max_asymmetry"):
            if (getattr(self, name) is not None) != has_hessian:
                state = "set" if has_hessian else "None"
                raise ValueError(f"{name} must be set iff hessian_hartree_per_bohr2 is ({state})")
        return self
