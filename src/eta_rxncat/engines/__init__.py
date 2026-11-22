"""Engine interfaces shared by every engine (v0.2.0).

Pure Python: importing this package loads no numpy, torch, RDKit, PySCF, MACE, fairchem or xtb.
Each engine imports its heavy library inside its own module, lazily.
"""

from eta_rxncat.engines.base import Engine, RawResult
from eta_rxncat.engines.errors import (
    EngineError,
    EngineInputError,
    EngineRuntimeError,
    EngineUnavailableError,
    ScfConvergenceError,
)
from eta_rxncat.engines.fd import fd_hessian
from eta_rxncat.engines.identity import library_version, model_id, sha256_file
from eta_rxncat.engines.options import (
    ENGINE_IMPL_KEY,
    OptionSpec,
    normalise_solvent,
    resolve_options,
    resolved_stage,
)
from eta_rxncat.engines.units import (
    BOHR_ANGSTROM,
    HARTREE_EV,
    HARTREE_KCAL_MOL,
    angstrom_to_bohr,
    bohr_to_angstrom,
    ev_per_angstrom_to_hartree_per_bohr,
    ev_to_hartree,
    kcal_mol_per_angstrom_to_hartree_per_bohr,
    kcal_mol_to_hartree,
)

__all__ = [
    "BOHR_ANGSTROM",
    "ENGINE_IMPL_KEY",
    "HARTREE_EV",
    "HARTREE_KCAL_MOL",
    "Engine",
    "EngineError",
    "EngineInputError",
    "EngineRuntimeError",
    "EngineUnavailableError",
    "OptionSpec",
    "RawResult",
    "ScfConvergenceError",
    "angstrom_to_bohr",
    "bohr_to_angstrom",
    "ev_per_angstrom_to_hartree_per_bohr",
    "ev_to_hartree",
    "fd_hessian",
    "kcal_mol_per_angstrom_to_hartree_per_bohr",
    "kcal_mol_to_hartree",
    "library_version",
    "model_id",
    "normalise_solvent",
    "resolve_options",
    "resolved_stage",
    "sha256_file",
]
