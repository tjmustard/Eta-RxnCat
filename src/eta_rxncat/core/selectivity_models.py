"""Selectivity contracts: TS conformer ensemble, its options and the selectivity result (v0.6.0).

Data only: pydantic and the standard library, no numpy and no RDKit (mission G8). The sampler,
the ensemble runner and the scorer compute the values; these models check their shape, the
weights and the closed reason sets (mission R7, R8, R16-R19, R25, §5 "Contracts").
"""

import re
from collections.abc import Iterable
from typing import Annotated, Any, Literal, Self

from pydantic import (
    Field,
    FiniteFloat,
    SerializerFunctionWrapHandler,
    StrictInt,
    field_validator,
    model_serializer,
    model_validator,
)

from eta_rxncat.core.models import (
    CoreModel,
    EngineIdentity,
    NonNegativeInt,
    PositiveFiniteFloat,
    PositiveInt,
)
from eta_rxncat.core.results import NonNegativeFiniteFloat
from eta_rxncat.core.ts_models import UnitInterval

_WEIGHT_SUM_TOL = 1e-12
_SHA256 = r"^[0-9a-f]{64}$"
_PATHWAY = r"^[A-Za-z][A-Za-z0-9_.-]*$"

_SOURCE = re.compile(r"^(seed|fragment_embed:(0|[1-9][0-9]*)|perturb:(0|[1-9][0-9]*))$")
_EXCLUSION_REASON = re.compile(
    r"^(ts_search_failed:\S.*|scf_convergence|engine_error|ts_validation_failed"
    r"|gate_failed:\S.*|face_mismatch|pre_relax_failed:\S.*|outside_window"
    r"|face_undetermined|connectivity_changed|orientation_mismatch"
    r"|seed_clash|bond_changed:(pre_relax|ts))$"
)

SelectivityKind = Literal["ee", "de", "regio"]
"""The selectivity quantity a result reports."""


def _signed_key(b: str, a: str) -> str:
    """Return the key of ``G_b - G_a`` in a signed-gap mapping: ``"<b>_vs_<a>"`` (mission R7)."""
    return f"{b}_vs_{a}"


def _check_signed_keys(keys: Iterable[str], pathways: Iterable[str]) -> None:
    """Raise unless every key is ``"<b>_vs_<a>"`` for two distinct names in ``pathways``."""
    names = list(pathways)
    allowed = {_signed_key(b, a) for b in names for a in names if a != b}
    unknown = sorted(set(keys) - allowed)
    if unknown:
        raise ValueError(f"signed_ddG_dagger_kcal_mol keys must be '<b>_vs_<a>' pairs: {unknown}")


def _check_source(value: str) -> str:
    if not _SOURCE.match(value):
        raise ValueError(f"source must be 'seed', 'fragment_embed:<k>' or 'perturb:<k>': {value!r}")
    return value


class SeedCheckDetail(CoreModel):
    """What a seed geometry check found (v0.7.0, slice 15).

    A ``clash`` sets the pair, its distance and its ratio (a graft's recorded contacts set only
    ``close_contact_count``); a ``bond_changed`` sets both bond lists.

    Attributes:
        check: ``clash`` or ``bond_changed``.
        pair: The clashing atom pair ``(i, j)`` with ``i < j``.
        distance_angstrom: Its distance.
        ratio_to_covalent_sum: The distance over the sum of the two covalent radii.
        bonds_formed: Bonds the geometry has that were not intended, sorted ``(i, j)`` pairs.
        bonds_broken: Intended bonds the geometry lacks, sorted ``(i, j)`` pairs.
        close_contact_count: Close contacts the graft recorded.
    """

    check: Literal["clash", "bond_changed"]
    pair: tuple[NonNegativeInt, NonNegativeInt] | None = None
    distance_angstrom: NonNegativeFiniteFloat | None = None
    ratio_to_covalent_sum: NonNegativeFiniteFloat | None = None
    bonds_formed: list[tuple[NonNegativeInt, NonNegativeInt]] | None = None
    bonds_broken: list[tuple[NonNegativeInt, NonNegativeInt]] | None = None
    close_contact_count: NonNegativeInt | None = None


class TSEnsembleOptions(CoreModel):
    """Every keyed number of the TS conformer search (mission R16-R18); all are recorded.

    Attributes:
        n_embed: Per-fragment ETKDG embeddings.
        n_perturb: Seeded Cartesian perturbations of the non-core atoms.
        perturb_sigma_angstrom: Perturbation standard deviation.
        pre_dedup_rmsd_angstrom: RMSD below which two samples are one before the search.
        random_seed: Seed of the sampler.
        max_research: Samples re-searched with P-RFO, besides the seed.
        rmsd_dedup_angstrom: RMSD below which two validated members may merge.
        flag_dG_kcal_mol: Free-energy difference above which a merge is flagged.
        energy_window_kcal_mol: Members above the lowest by more than this are not summed.
        max_automorphisms: Cap on the automorphism count used by the RMSD comparison.
    """

    n_embed: PositiveInt = 10
    n_perturb: PositiveInt = 10
    perturb_sigma_angstrom: PositiveFiniteFloat = 0.3
    pre_dedup_rmsd_angstrom: PositiveFiniteFloat = 0.125
    random_seed: StrictInt = 42
    max_research: PositiveInt = 10
    rmsd_dedup_angstrom: PositiveFiniteFloat = 0.125
    flag_dG_kcal_mol: PositiveFiniteFloat = 0.05
    energy_window_kcal_mol: PositiveFiniteFloat = 3.0
    max_automorphisms: PositiveInt = 100000


class TSEnsembleMember(CoreModel):
    """One validated, face-consistent TS conformer that enters the Boltzmann sum.

    Attributes:
        index: Index of the member within its ensemble.
        source: ``seed``, ``fragment_embed:<k>`` or ``perturb:<k>``.
        start_sha256: Digest of the start geometry the search began from.
        G_hartree: Gibbs free energy (Eh).
        degeneracy: Symmetry degeneracy g (>= 1) of the member.
        rmsd_to_seed_angstrom: RMSD of the member to the seed TS.
        face: Face descriptor, one entry per forming bond, each +1 or -1.
        validation_passed_bool: Whether the TS validation passed.
        weight: Boltzmann weight in [0, 1]; the weights of an ensemble sum to 1.
        pre_relax_wall_time_s: Wall time of the pre-relaxation, if one ran (mission R25).
    """

    index: NonNegativeInt
    source: str
    start_sha256: str = Field(pattern=_SHA256)
    G_hartree: FiniteFloat
    degeneracy: PositiveInt
    rmsd_to_seed_angstrom: NonNegativeFiniteFloat
    face: list[StrictInt] = Field(min_length=1)
    validation_passed_bool: bool
    weight: UnitInterval
    pre_relax_wall_time_s: NonNegativeFiniteFloat | None = None

    @field_validator("source")
    @classmethod
    def _source(cls, value: str) -> str:
        return _check_source(value)

    @field_validator("face")
    @classmethod
    def _face(cls, value: list[int]) -> list[int]:
        if any(entry not in (-1, 1) for entry in value):
            raise ValueError(f"face entries must be +1 or -1, got {value}")
        return value


class TSEnsembleExclusion(CoreModel):
    """One sample left out of the sum, with the reason (mission R19).

    Attributes:
        index: Index of the sample.
        source: ``seed``, ``fragment_embed:<k>`` or ``perturb:<k>``.
        reason: ``ts_search_failed:<reason>``, ``scf_convergence``, ``engine_error``,
            ``ts_validation_failed``, ``gate_failed:<check>``, ``face_mismatch``,
            ``pre_relax_failed:<error>``, ``outside_window``, ``face_undetermined``,
            ``connectivity_changed``, ``orientation_mismatch``, ``seed_clash`` or
            ``bond_changed:<stage>`` (``pre_relax`` or ``ts``).
        pre_relax_wall_time_s: Wall time of the pre-relaxation, if one ran (mission R25).
        detail: What a seed check found; left out of the serialised form when ``None``.
    """

    index: NonNegativeInt
    source: str
    reason: str
    pre_relax_wall_time_s: NonNegativeFiniteFloat | None = None
    detail: SeedCheckDetail | None = None

    @model_serializer(mode="wrap")
    def _omit_absent_detail(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        data: dict[str, Any] = handler(self)
        if self.detail is None:
            data.pop("detail", None)
        return data

    @field_validator("source")
    @classmethod
    def _source(cls, value: str) -> str:
        return _check_source(value)

    @field_validator("reason")
    @classmethod
    def _reason(cls, value: str) -> str:
        if not _EXCLUSION_REASON.match(value):
            raise ValueError(f"unknown exclusion reason {value!r}")
        return value


class TSEnsembleMerge(CoreModel):
    """Two members merged by the RMSD deduplication.

    Attributes:
        kept_index: Index of the member that stays.
        merged_index: Index of the member folded into it.
        dG_kcal_mol: Free-energy difference between the two (kcal/mol).
        rmsd_angstrom: Their RMSD (Angstrom).
    """

    kept_index: NonNegativeInt
    merged_index: NonNegativeInt
    dG_kcal_mol: FiniteFloat
    rmsd_angstrom: NonNegativeFiniteFloat

    @model_validator(mode="after")
    def _distinct(self) -> Self:
        if self.kept_index == self.merged_index:
            raise ValueError("a member cannot merge into itself")
        return self


class TSEnsemble(CoreModel):
    """The Boltzmann-summed TS conformers of one pathway.

    Attributes:
        pathway: The pathway label.
        temperature_k: Temperature of the sum (K).
        reactant_key: Sorted ``(SMILES, count)`` pairs of the reactants.
        recipe_identity: The engine (name, model, version) that scored every member.
        members: The summed members; their weights sum to 1 within 1e-12.
        excluded: Samples left out, each with its reason.
        merges: Deduplication merges.
        flagged_merges: Merges whose free-energy difference exceeded ``flag_dG_kcal_mol``.
        options: The keyed search options.
        G_pathway_hartree: Pathway free energy ``-RT ln sum g_i exp(-G_i/RT)`` (Eh); ``None``
            when the pathway failed.
        failed_reason: Why the pathway failed; ``None`` when it did not.
        failed_detail: What a seed check found on a failed seed; left out of the serialised form
            when ``None``.
    """

    pathway: str = Field(pattern=_PATHWAY)
    temperature_k: PositiveFiniteFloat
    reactant_key: tuple[tuple[str, PositiveInt], ...]
    recipe_identity: EngineIdentity
    members: list[TSEnsembleMember] = Field(default_factory=list)
    excluded: list[TSEnsembleExclusion] = Field(default_factory=list)
    merges: list[TSEnsembleMerge] = Field(default_factory=list)
    flagged_merges: list[TSEnsembleMerge] = Field(default_factory=list)
    options: TSEnsembleOptions = Field(default_factory=TSEnsembleOptions)
    G_pathway_hartree: FiniteFloat | None = None
    failed_reason: str | None = Field(default=None, min_length=1)
    failed_detail: SeedCheckDetail | None = None

    @model_serializer(mode="wrap")
    def _omit_absent_detail(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        data: dict[str, Any] = handler(self)
        if self.failed_detail is None:
            data.pop("failed_detail", None)
        return data

    @model_validator(mode="after")
    def _check_ensemble(self) -> Self:
        if self.G_pathway_hartree is not None and self.failed_reason is not None:
            raise ValueError("G_pathway_hartree and failed_reason are mutually exclusive")
        if not self.members and self.G_pathway_hartree is not None:
            raise ValueError("G_pathway_hartree needs at least one summed member")
        if self.members:
            total = sum(m.weight for m in self.members)
            if abs(total - 1.0) > _WEIGHT_SUM_TOL:
                raise ValueError(f"member weights sum to {total!r}, not 1 within 1e-12")
            indices = [m.index for m in self.members]
            if len(set(indices)) != len(indices):
                raise ValueError(f"duplicate member indices in {indices}")
        return self


class PruningDecision(CoreModel):
    """The outcome of evaluating one ``PathwayPruningRule`` (mission R7, G2).

    Attributes:
        rule_id: The rule evaluated.
        pathways: The two compared pathways.
        ddG_dagger_kcal_mol: Unsigned gap between the pathways, ``None`` when it could not be
            computed (a pathway had no valid member).
        signed_ddG_dagger_kcal_mol: ``"<b>_vs_<a>"`` -> ``G_b - G_a`` (kcal/mol) with ``(a, b)``
            in rule order (mission R7); empty when uncomputed.
        threshold_kcal_mol: The rule's threshold.
        pruned_node_ids: Ids of the pruned nodes, sorted and unique.
        reason: Why the decision came out this way.
    """

    rule_id: str
    pathways: tuple[str, str]
    ddG_dagger_kcal_mol: NonNegativeFiniteFloat | None
    signed_ddG_dagger_kcal_mol: dict[str, FiniteFloat] = Field(default_factory=dict)
    threshold_kcal_mol: PositiveFiniteFloat
    pruned_node_ids: list[str] = Field(default_factory=list)
    reason: str = Field(min_length=1)

    @field_validator("pruned_node_ids")
    @classmethod
    def _sorted_unique(cls, value: list[str]) -> list[str]:
        if value != sorted(set(value)):
            raise ValueError(f"pruned_node_ids must be sorted and unique, got {value}")
        return value

    @model_validator(mode="after")
    def _check_signed(self) -> Self:
        _check_signed_keys(self.signed_ddG_dagger_kcal_mol, self.pathways)
        return self


class PathwaySelectivity(CoreModel):
    """One pathway's line in a ``SelectivityResult``.

    Attributes:
        G_pathway_hartree: The pathway free energy (Eh).
        n_members: Members summed.
        n_excluded: Samples excluded.
        fraction: The pathway's share of the product, in [0, 1].
    """

    G_pathway_hartree: FiniteFloat
    n_members: NonNegativeInt
    n_excluded: NonNegativeInt
    fraction: UnitInterval


class SelectivityResult(CoreModel):
    """ΔΔG‡, the rate ratio and the selectivity of competing pathways (mission US-004).

    Attributes:
        ddG_dagger_kcal_mol: Gap between the minor and the major pathway (>= 0).
        signed_ddG_dagger_kcal_mol: ``"<b>_vs_<a>"`` -> ``G_b - G_a`` (kcal/mol), both names in
            ``per_pathway`` (mission R7); never empty.
        ratio: ``exp(ddG/RT)``, major over minor (>= 1); ``inf`` only when that overflows a float.
        selectivity_percent: ``100 (r - 1)/(r + 1)``, in [0, 100].
        kind: ``ee``, ``de`` or ``regio``.
        major_pathway: The lowest-barrier pathway.
        temperature_k: Temperature (K).
        per_pathway: Each pathway's free energy, counts and fraction.
        pruning: The pruning decision, if a rule was evaluated.
    """

    ddG_dagger_kcal_mol: NonNegativeFiniteFloat
    signed_ddG_dagger_kcal_mol: dict[str, FiniteFloat]
    ratio: Annotated[float, Field(ge=1.0, allow_inf_nan=True)]
    selectivity_percent: Annotated[float, Field(ge=0.0, le=100.0, allow_inf_nan=False)]
    kind: SelectivityKind
    major_pathway: str
    temperature_k: PositiveFiniteFloat
    per_pathway: dict[str, PathwaySelectivity] = Field(min_length=2)
    pruning: PruningDecision | None = None

    @model_validator(mode="after")
    def _check_result(self) -> Self:
        if self.major_pathway not in self.per_pathway:
            raise ValueError(f"major_pathway {self.major_pathway!r} is not in per_pathway")
        if not self.signed_ddG_dagger_kcal_mol:
            raise ValueError("signed_ddG_dagger_kcal_mol must not be empty")
        _check_signed_keys(self.signed_ddG_dagger_kcal_mol, self.per_pathway)
        return self
