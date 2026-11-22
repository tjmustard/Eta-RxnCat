"""Engine interfaces shared by every engine (v0.2.0).

Pure Python: importing this package loads no numpy, torch, RDKit, PySCF, MACE, fairchem or xtb.
Each engine imports its heavy library inside its own methods, lazily.
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
from eta_rxncat.engines.mace import MACEEngine
from eta_rxncat.engines.options import (
    ENGINE_IMPL_KEY,
    OptionSpec,
    normalise_solvent,
    resolve_options,
    resolved_stage,
)
from eta_rxncat.engines.pyscf_gpu_cpu import PySCFEngine
from eta_rxncat.engines.rdkit_ff import RDKitFFEngine
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
from eta_rxncat.engines.xtb_subprocess import XTBSubprocessEngine

__all__ = [
    "BOHR_ANGSTROM",
    "ENGINE_IMPL_KEY",
    "HARTREE_EV",
    "HARTREE_KCAL_MOL",
    "MACEEngine",
    "Engine",
    "EngineError",
    "EngineInputError",
    "EngineRuntimeError",
    "EngineUnavailableError",
    "OptionSpec",
    "PySCFEngine",
    "RDKitFFEngine",
    "RawResult",
    "ScfConvergenceError",
    "XTBSubprocessEngine",
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
