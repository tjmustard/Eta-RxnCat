"""The ``RunRecord`` exporter input and the versioned ``RunData`` v1 contract (v0.7.0, slice 07).

``RunData`` is the one public document every view reads (mission R12, R15): self-contained, every
unit in its key, ids referenced by id, reason **codes** only, never a message, path, user name,
host name or timestamp. It embeds no core model, so its JSON Schema comes from these classes alone.

``RunData`` is the strict writer (unknown keys refused, ``schema_version`` exactly 1).
``read_run_data`` is the lenient reader: a parallel model tree that ignores unknown keys and
refuses a later version.
"""

import json
import types
from collections.abc import Iterable
from typing import Annotated, Any, Literal, Self, Union, get_args, get_origin

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    StrictInt,
    create_model,
    field_validator,
    model_validator,
)

from eta_rxncat.core import (
    EngineIdentity,
    FallbackRecord,
    GraftRecord,
    MolecularState,
    OptimizerIdentity,
    SelectivityResult,
    ThermoAnalysisOptions,
    TSEnsemble,
)

SCHEMA_VERSION = 1
"""The ``RunData`` version this module writes."""

CHANGES: tuple[tuple[int, str], ...] = ((1, "First version (eta-rxncat v0.7.0)."),)
"""``(schema_version, what changed)``, oldest first."""

Code = Annotated[str, Field(pattern=r"^[A-Za-z0-9_.:+=,@-]+$")]
"""A reason or label code: no spaces and no slashes, so no message and no path fits."""

StageKeyHex = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
"""A stage key: the store's primary key (sha256 hex)."""

Name = Annotated[str, Field(min_length=1)]
UnitInterval = Annotated[float, Field(ge=0.0, le=1.0)]
NonNegative = Annotated[float, Field(ge=0.0)]
Count = Annotated[StrictInt, Field(ge=0)]
Index = Annotated[StrictInt, Field(ge=0)]
Positive = Annotated[StrictInt, Field(ge=1)]
Xyz = list[list[FiniteFloat]]

TrajectoryKind = Literal["pre_relax", "ts_search", "endpoint_opt"]
GateUnit = Literal["angstrom", "kcal_mol", "hartree", "cm1", "count", "fraction"]


class UnsupportedRunDataVersion(ValueError):
    """The document's ``schema_version`` is newer than this reader understands."""


# --- RunRecord: the exporter's input ---------------------------------------------------------


class _Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class RecordSpecies(_Record):
    """A species the run refers to by id.

    Attributes:
        species_id: Unique id.
        label: Display label.
        state: The structure: symbols and atom order of every row that refers to it.
    """

    species_id: Name
    label: Name
    state: MolecularState


class RecordCandidate(_Record):
    """One enumerated candidate (an ``EnumeratedCandidate`` by id) and its graft records.

    Attributes:
        candidate_id: The candidate id.
        entry_ids_by_site: The library entry chosen at each site.
        records: Every graft record behind the candidate, refusals included.
    """

    candidate_id: Name
    entry_ids_by_site: dict[str, str]
    records: list[GraftRecord] = Field(default_factory=list)


class RecordSample(_Record):
    """The cached rows of one TS sample of one template.

    Attributes:
        template_id: The (grafted) template whose ensemble the sample belongs to.
        sample_index: The sample's index in that ensemble; 0 is the seed.
        source: ``seed``, ``fragment_embed:<k>`` or ``perturb:<k>``.
        species_id: The species giving the rows' symbols and atom order.
        pre_relax_key: The ``constrained_preopt`` row, if the sample was pre-relaxed.
        ts_opt_key: The ``ts_opt`` row, if the sample was searched.
        frequency_key: The ``frequency`` row at the found TS, if computed.
    """

    template_id: Name
    sample_index: Index
    source: Code
    species_id: Name
    pre_relax_key: StageKeyHex | None = None
    ts_opt_key: StageKeyHex | None = None
    frequency_key: StageKeyHex | None = None


class RecordEndpoint(_Record):
    """The cached rows of one endpoint (reactant) species run.

    Attributes:
        species_id: The species.
        opt_keys: Its ``geometry_opt`` rows.
        frequency_keys: Its ``frequency`` rows.
    """

    species_id: Name
    opt_keys: list[StageKeyHex] = Field(default_factory=list)
    frequency_keys: list[StageKeyHex] = Field(default_factory=list)


class RecordRun(_Record):
    """One candidate x pathway x engine unit.

    Attributes:
        candidate_id: The candidate.
        pathway: The pathway label.
        engine: The engine that ran it.
        optimizers: The optimizers it used.
        species_id: The unit's transition-state species (its charge and multiplicity).
        analysis: The normal-mode options the run gated its frequencies with.
        fallback: The fallback record of the pathway's node.
        ensemble: The TS ensemble, when a template yielded one.
        stall_cap_reached_bool: Whether sampling stopped at the stall cap.
        dG_dagger_kcal_mol: Activation free energy, if computed.
        samples: The rows of every TS sample.
        endpoints: The rows of every endpoint species.
    """

    candidate_id: Name
    pathway: Name
    engine: EngineIdentity
    optimizers: list[OptimizerIdentity] = Field(default_factory=list)
    species_id: Name
    analysis: ThermoAnalysisOptions
    fallback: FallbackRecord
    ensemble: TSEnsemble | None = None
    stall_cap_reached_bool: bool = False
    dG_dagger_kcal_mol: FiniteFloat | None = None
    samples: list[RecordSample] = Field(default_factory=list)
    endpoints: list[RecordEndpoint] = Field(default_factory=list)


class RecordSelectivity(_Record):
    """The selectivity result of one candidate on one engine.

    Attributes:
        candidate_id: The candidate.
        engine: The engine that scored it.
        result: The selectivity result.
    """

    candidate_id: Name
    engine: EngineIdentity
    result: SelectivityResult


class RecordUnitRef(_Record):
    """A reference to one ``RecordRun``."""

    candidate_id: Name
    pathway: Name
    engine: EngineIdentity


class RecordGate(_Record):
    """One mechanics gate, as the run judged it.

    Attributes:
        gate_id: The gate's code.
        unit_ref: The run it judged; ``None`` for a gate over the whole record.
        pass_bool: Whether it passed.
        value: The measured value, if it has one.
        unit: The unit of ``value`` and ``threshold``.
        threshold: The threshold, if it has one.
        detail_code: A code explaining the verdict.
    """

    gate_id: Code
    unit_ref: RecordUnitRef | None = None
    pass_bool: bool
    value: FiniteFloat | None = None
    unit: GateUnit | None = None
    threshold: FiniteFloat | None = None
    detail_code: Code | None = None


class RunRecord(_Record):
    """What ran: the input of ``export_run_data``, which resolves its rows from a store.

    Attributes:
        record_version: Version of this input model (not of ``RunData``).
        species: Every species referred to by id.
        candidates: The enumerated candidates.
        runs: One entry per candidate x pathway x engine.
        selectivity: Selectivity results per candidate and engine.
        gates: Mechanics gates.
    """

    record_version: Literal[1] = 1
    species: list[RecordSpecies] = Field(default_factory=list)
    candidates: list[RecordCandidate] = Field(default_factory=list)
    runs: list[RecordRun] = Field(default_factory=list)
    selectivity: list[RecordSelectivity] = Field(default_factory=list)
    gates: list[RecordGate] = Field(default_factory=list)


# --- RunData: the public contract ------------------------------------------------------------


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class EngineEntry(_Strict):
    """An engine identity: tag, version and, for a model engine, its content-hashed model id."""

    engine_id: Name
    name: Code
    version: Name
    model: Name | None

    @field_validator("version", "model")
    @classmethod
    def _no_path(cls, value: str | None) -> str | None:
        if value is not None and (value.startswith(("/", "~")) or "\\" in value):
            raise ValueError("an engine identity must not be a file path")
        return value


class OptimizerEntry(_Strict):
    """An optimizer identity."""

    name: Code
    version: Code


class ThermoOptionsEntry(_Strict):
    """The normal-mode and symmetry tolerances of a run."""

    thermo_options_id: Name
    imag_tol_cm1: NonNegative
    sym_tol_angstrom: NonNegative
    linear_tol_angstrom: NonNegative
    max_automorphisms: Positive


class StageKeyEntry(_Strict):
    """One stage row the document was exported from."""

    stage_kind: Literal["constrained_preopt", "ts_opt", "frequency", "geometry_opt"]
    stage_key: StageKeyHex


class Provenance(_Strict):
    """Where the document came from; the store is named by its file name only."""

    eta_version: Name
    store_file_name: Annotated[str, Field(min_length=1, pattern=r"^[^/\\]+$")]
    engines: list[EngineEntry]
    optimizers: list[OptimizerEntry]
    thermo_options: list[ThermoOptionsEntry]
    stage_keys: list[StageKeyEntry]


class Species(_Strict):
    """One species: atom identity and its input geometry."""

    species_id: Name
    label: Name
    symbols: list[Code]
    coordinates_angstrom: Xyz
    charge: StrictInt
    spin_multiplicity: Positive
    active_atom_indices: list[Index]


class ImaginaryMode(_Strict):
    """An imaginary mode: the Cartesian displacement per atom, unit length over all components.

    The displacement is a direction; a viewer scales it. Its sign is fixed so that the component
    of largest magnitude is positive.
    """

    frequency_cm1: FiniteFloat
    displacements_angstrom: Xyz


class FrequencyCompleted(_Strict):
    """Frequencies recomputed from the stored Hessian with the run's own options."""

    status: Literal["completed"]
    frequency_id: Name
    species_id: Name
    stage_key: StageKeyHex
    coordinates_angstrom: Xyz
    frequencies_cm1: list[FiniteFloat]
    n_imaginary: Count
    imag_tol_cm1: NonNegative
    imaginary_modes: list[ImaginaryMode]


class FrequencyFailed(_Strict):
    """A frequency row that records a failure."""

    status: Literal["failed"]
    frequency_id: Name
    species_id: Name
    stage_key: StageKeyHex
    failed_code: Code


class FrequencyMissing(_Strict):
    """A frequency row the store does not hold; it is never recomputed."""

    status: Literal["missing"]
    frequency_id: Name
    species_id: Name
    stage_key: StageKeyHex


FrequencyEntry = Annotated[
    FrequencyCompleted | FrequencyFailed | FrequencyMissing, Field(discriminator="status")
]


class Frame(_Strict):
    """One geometry an optimizer evaluated."""

    coordinates_angstrom: Xyz
    energy_hartree: FiniteFloat
    max_gradient_hartree_per_bohr: NonNegative
    accepted_bool: bool | None
    ladder_step: Code | None


class Convergence(_Strict):
    """How an optimization ended; ``None`` where the stored row holds no such number."""

    converged_bool: bool
    failed_code: Code | None
    n_steps: Count | None
    n_engine_calls: Count | None
    final_energy_hartree: FiniteFloat | None
    final_max_gradient_hartree_per_bohr: NonNegative | None
    recovery_steps: list[Code]


class TrajectoryStored(_Strict):
    """The stored frames of one optimization, possibly decimated.

    ``frames`` keeps every ``decimation_stride``-th frame and the last one; ``n_frames_total`` is
    the full count in the store. A row without frames has none (no trajectory stored).
    """

    status: Literal["stored"]
    trajectory_id: Name
    kind: TrajectoryKind
    species_id: Name
    label: Name
    stage_key: StageKeyHex
    frames: list[Frame]
    n_frames_total: Count
    decimation_stride: Positive
    convergence: Convergence


class TrajectoryMissing(_Strict):
    """An optimization row the store does not hold."""

    status: Literal["missing"]
    trajectory_id: Name
    kind: TrajectoryKind
    species_id: Name
    label: Name
    stage_key: StageKeyHex


TrajectoryEntry = Annotated[TrajectoryStored | TrajectoryMissing, Field(discriminator="status")]


class FallbackAttemptCode(_Strict):
    """One template tried as the TS seed, with the reason as a code."""

    template_id: Name
    rank: Positive
    outcome: Literal["chosen", "fell_through", "stopped"]
    reason_code: Code | None


class GraftRefusal(_Strict):
    """A graft onto the pathway's node that was refused."""

    template_id: Name
    site_id: Name
    entry_id: Name
    reason_code: Code


class Member(_Strict):
    """One summed TS conformer and its rows."""

    member_index: Index
    source: Code
    weight_fraction: UnitInterval
    gibbs_free_energy_hartree: FiniteFloat
    degeneracy: Positive
    rmsd_to_seed_angstrom: NonNegative
    frequency_id: Name | None
    trajectory_ids: list[Name]


class Candidate(_Strict):
    """One candidate x pathway x engine unit.

    ``dG_dagger_kcal_mol`` is the run's activation free energy. ``ddG_dagger_kcal_mol`` is the
    gap of the candidate's selectivity result on this engine (minor minus major pathway), the same
    on every pathway it compares. ``graft_rmsd_angstrom`` is the largest alignment RMSD of the
    grafts behind the chosen template. ``frequency_ids`` and ``trajectory_ids`` are the
    transition-state samples; the ``endpoint_*`` ids are the minima.
    """

    candidate_entry_id: Name
    candidate_id: Name
    entry_ids_by_site: dict[str, str]
    pathway: Name
    node_id: Name
    engine_id: Name
    thermo_options_id: Name
    species_id: Name
    charge: StrictInt
    spin_multiplicity: Positive
    template_rank_used: Positive | None
    chosen_template_id: Name | None
    stop_reason_code: Code | None
    fallback_attempts: list[FallbackAttemptCode]
    graft_refusals: list[GraftRefusal]
    dG_dagger_kcal_mol: FiniteFloat | None
    ddG_dagger_kcal_mol: NonNegative | None
    graft_rmsd_angstrom: NonNegative | None
    stall_cap_reached_bool: bool
    members: list[Member]
    frequency_ids: list[Name]
    trajectory_ids: list[Name]
    endpoint_frequency_ids: list[Name]
    endpoint_trajectory_ids: list[Name]


class Gate(_Strict):
    """A mechanics gate; ``value`` and ``threshold`` are in ``unit``."""

    gate_id: Code
    candidate_entry_id: Name | None
    pass_bool: bool
    value: FiniteFloat | None
    unit: GateUnit | None
    threshold: FiniteFloat | None
    detail_code: Code | None


def _require_unique(name: str, ids: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    for item in ids:
        if item in seen:
            raise ValueError(f"duplicate {name} {item!r}")
        seen.add(item)
    return seen


def _require_known(name: str, ids: Iterable[str], known: set[str]) -> None:
    unknown = sorted(set(ids) - known)
    if unknown:
        raise ValueError(f"unknown {name} reference(s): {unknown}")


class RunData(_Strict):
    """The eta-rxncat run-data document, version 1.

    Version rule: additive optional keys keep the version; removing, renaming or retyping a key,
    changing a unit or a meaning, or adding an enum value bumps it. The writer always emits the
    current version. Every key with a physical unit carries it in its name (a gate's value and
    threshold carry it in ``unit``). Every reference is an id of another entry of the document.
    """

    schema_version: Literal[1]
    provenance: Provenance
    species: list[Species]
    frequencies: list[FrequencyEntry]
    trajectories: list[TrajectoryEntry]
    candidates: list[Candidate]
    gates: list[Gate]

    @field_validator("schema_version", mode="before")
    @classmethod
    def _strict_version(cls, value: object) -> object:
        # Literal[1] alone would accept True and 1.0.
        if type(value) is not int:
            raise ValueError(f"schema_version must be the integer 1, not {value!r}")
        return value

    @model_validator(mode="after")
    def _check_references(self) -> Self:
        species = _require_unique("species_id", (s.species_id for s in self.species))
        frequencies = _require_unique("frequency_id", (f.frequency_id for f in self.frequencies))
        trajectories = _require_unique(
            "trajectory_id", (t.trajectory_id for t in self.trajectories)
        )
        candidates = _require_unique(
            "candidate_entry_id", (c.candidate_entry_id for c in self.candidates)
        )
        engines = {e.engine_id for e in self.provenance.engines}
        thermo = {t.thermo_options_id for t in self.provenance.thermo_options}
        _require_known("species", (f.species_id for f in self.frequencies), species)
        _require_known("species", (t.species_id for t in self.trajectories), species)
        for c in self.candidates:
            _require_known("species", [c.species_id], species)
            _require_known("engine", [c.engine_id], engines)
            _require_known("thermo options", [c.thermo_options_id], thermo)
            member_frequencies = [m.frequency_id for m in c.members if m.frequency_id]
            _require_known(
                "frequency",
                [*c.frequency_ids, *c.endpoint_frequency_ids, *member_frequencies],
                frequencies,
            )
            _require_known(
                "trajectory",
                [
                    *c.trajectory_ids,
                    *c.endpoint_trajectory_ids,
                    *(t for m in c.members for t in m.trajectory_ids),
                ],
                trajectories,
            )
        _require_known(
            "candidate",
            (g.candidate_entry_id for g in self.gates if g.candidate_entry_id),
            candidates,
        )
        return self


# --- The lenient reader ----------------------------------------------------------------------

_LENIENT: dict[type[BaseModel], type[BaseModel]] = {}


def _relax(annotation: Any) -> Any:
    """Return ``annotation`` with every model in it replaced by its lenient twin."""
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return _lenient_model(annotation)
    origin = get_origin(annotation)
    if origin is Annotated:
        return Annotated[(_relax(annotation.__origin__), *annotation.__metadata__)]
    if origin in (list, dict):
        return origin[tuple(_relax(a) for a in get_args(annotation))]
    if origin in (Union, types.UnionType):
        return Union[tuple(_relax(a) for a in get_args(annotation))]  # noqa: UP007
    return annotation


def _lenient_model(model: type[BaseModel]) -> type[BaseModel]:
    """Return the twin of a strict model that ignores unknown keys (built once).

    Every field of the tree is required, and each keeps its type but not its constraints: the
    strict model checks those afterwards.
    """
    if model not in _LENIENT:
        fields: dict[str, Any] = {
            name: (_relax(info.annotation), ...) for name, info in model.model_fields.items()
        }
        if model is RunData:
            fields["schema_version"] = (int, ...)
        _LENIENT[model] = create_model(
            f"Lenient{model.__name__}", __config__=ConfigDict(extra="ignore"), **fields
        )
    return _LENIENT[model]


def read_run_data(data: bytes) -> RunData:
    """Read a run-data document, ignoring keys this version does not know.

    Raises:
        UnsupportedRunDataVersion: ``schema_version`` is above ``SCHEMA_VERSION``.
        ValueError: Not JSON, or not a valid document (``pydantic.ValidationError``).
    """
    document = json.loads(data)
    if isinstance(document, dict):
        version = document.get("schema_version")
        if isinstance(version, int) and version > SCHEMA_VERSION:
            raise UnsupportedRunDataVersion(
                f"run-data schema_version {version} is newer than {SCHEMA_VERSION}"
            )
    relaxed = _lenient_model(RunData).model_validate(document)
    return RunData.model_validate(relaxed.model_dump())
