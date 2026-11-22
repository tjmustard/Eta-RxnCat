"""Static dielectric constants for the PySCF engine's ddCOSMO / C-PCM solvation (mission R2).

Source: the Minnesota Solvent Descriptor Database (https://comp.chem.umn.edu/solvation/mnsddb.pdf),
epsilon column, except water, which is 78.3553 (PySCF's ``ddcosmo.EPS_WATER``). The values were
checked (v0.2.0 slice 06) against the copies shipped in PySCF 2.15.1
(``pyscf/solvent/_solvent_data.py``) and GPU4PySCF 1.9.2 (``gpu4pyscf/solvent/_solvent_data.py``):
the two copies have identical epsilons for all 180 entries, and every value here equals them
(tested). Keys are lowercase; ``StageConfig.solvation.solvent`` is lowercased before lookup.
"""

from types import MappingProxyType
from typing import Final

DIELECTRICS: Final = MappingProxyType(
    {
        "water": 78.3553,
        "toluene": 2.3741,
        "acetonitrile": 35.688,
        "methanol": 32.613,
        "ethanol": 24.852,
        "dichloromethane": 8.93,
        "tetrahydrofuran": 7.4257,
        "dimethylsulfoxide": 46.826,
        "benzene": 2.2706,
        "chloroform": 4.7113,
        "acetone": 20.493,
        "n,n-dimethylformamide": 37.219,
        "n-hexane": 1.8819,
        "diethylether": 4.24,
        "1,4-dioxane": 2.2099,
        "pyridine": 12.978,
        "nitromethane": 36.562,
        "cyclohexane": 2.0165,
        "2-propanol": 19.264,
        "chlorobenzene": 5.6968,
    }
)
"""Lowercase solvent name -> static dielectric constant (dimensionless)."""

SOURCE: Final = "Minnesota Solvent Descriptor Database (mnsddb); water 78.3553 per PySCF ddcosmo"
"""Where the table comes from (recorded for reports)."""
