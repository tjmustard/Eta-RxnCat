"""Keyed conformer options (mission §5 Contracts; R3, R21)."""

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt

from eta_rxncat.core.models import PositiveFiniteFloat, ScalarValue


class ConformerOptions(BaseModel):
    """Every option that changes a conformer result; the runner keys them.

    Attributes:
        n_embed: Embeddings per ETKDG pass.
        seed: ETKDG random seed (both passes).
        torsion_free_pass: Run the second pass without experimental torsion preferences (R21).
        pre_dedup_rmsd_angstrom: RMSD (with H) below which a pool member duplicates a kept one.
        rmsd_dedup_angstrom: RMSD below which two optimized conformers are one.
        energy_window_kcal_mol: Keep optimized conformers within this of the lowest.
        include_h_in_rmsd: Use hydrogens in the post-optimization dedup RMSD.
        max_automorphisms: Cap on graph automorphisms; reaching it is an error.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    n_embed: StrictInt = Field(default=50, ge=1)
    seed: StrictInt = Field(default=42, ge=0)
    torsion_free_pass: StrictBool = True
    pre_dedup_rmsd_angstrom: PositiveFiniteFloat = 0.125
    rmsd_dedup_angstrom: PositiveFiniteFloat = 0.125
    energy_window_kcal_mol: PositiveFiniteFloat = 6.0
    include_h_in_rmsd: StrictBool = True
    max_automorphisms: StrictInt = Field(default=100000, ge=1)

    def as_stage_options(self) -> dict[str, ScalarValue]:
        """Return every option, sorted by key, as scalar stage options."""
        return {key: getattr(self, key) for key in sorted(type(self).model_fields)}
