"""Export a run from the artifact store, and serialise it canonically (v0.7.0, slice 07).

The exporter resolves each stage key of a ``RunRecord`` to its cached row. It never runs an engine
and never recomputes a result: a row the store does not hold is exported as ``missing``. The one
derivation is the normal modes of a stored Hessian (``thermo.normal_modes`` with the run's own
options, so the listed frequencies are the gated ones). Only allow-listed fields leave a row; its
``message`` never does (mission R15).
"""

import json
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import numpy as np

import eta_rxncat
from eta_rxncat.core import (
    EngineIdentity,
    OptimizationFrame,
    ThermoAnalysisOptions,
    TSSearchResult,
)
from eta_rxncat.review.run_data import (
    SCHEMA_VERSION,
    Candidate,
    Convergence,
    EngineEntry,
    FallbackAttemptCode,
    Frame,
    FrequencyCompleted,
    FrequencyEntry,
    FrequencyFailed,
    FrequencyMissing,
    Gate,
    GraftRefusal,
    ImaginaryMode,
    Member,
    OptimizerEntry,
    Provenance,
    RecordCandidate,
    RecordRun,
    RecordSpecies,
    RecordUnitRef,
    RunData,
    RunRecord,
    Species,
    StageKeyEntry,
    ThermoOptionsEntry,
    TrajectoryEntry,
    TrajectoryKind,
    TrajectoryMissing,
    TrajectoryStored,
)
from eta_rxncat.store import KEY_SCHEMA, ArtifactStore, StageKey, grid_coordinate
from eta_rxncat.thermo import normal_modes

_SIGNIFICANT_DIGITS: tuple[tuple[str, int], ...] = (
    # (key suffix, significant digits); the first match wins.
    ("_hartree_per_bohr", 8),
    ("_hartree", 12),
    ("_angstrom", 10),
    ("_cm1", 8),
    ("_kcal_mol", 8),
)
_DEFAULT_DIGITS = 12
"""Digits of a float whose key names no unit family (fractions, gate values)."""

_HTML_ESCAPES = (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026"))


class ExportError(ValueError):
    """The record and the store do not fit together; nothing is exported."""


class ExportBudgetError(ExportError):
    """Even the coarsest decimation exceeds the trajectory byte budget."""


# --- Canonical serialisation -----------------------------------------------------------------


def _rounded(value: Any, digits: int) -> Any:
    """Return ``value`` with every float rounded; a key's family covers all it contains."""
    if isinstance(value, float):
        rounded = float(f"{value:.{digits}g}")
        return 0.0 if rounded == 0.0 else rounded
    if isinstance(value, list):
        return [_rounded(item, digits) for item in value]
    if isinstance(value, dict):
        return {
            key: _rounded(
                item,
                next((n for s, n in _SIGNIFICANT_DIGITS if key.endswith(s)), _DEFAULT_DIGITS),
            )
            for key, item in value.items()
        }
    return value


def _canonical_bytes(value: Any) -> bytes:
    text = json.dumps(
        _rounded(value, _DEFAULT_DIGITS),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,  # writes U+2028 and U+2029 as   and
        allow_nan=False,
    )
    # These characters occur only inside JSON strings, so replacing them keeps the JSON valid.
    for char, escape in _HTML_ESCAPES:
        text = text.replace(char, escape)
    return text.encode("ascii")


def canonical_run_data_json(run_data: RunData) -> bytes:
    r"""Return the one serialisation of ``run_data`` (mission R14).

    Keys are sorted, separators compact, floats rounded to a fixed number of significant digits
    per unit family and written by ``repr``, and ``<``, ``>``, ``&``, U+2028 and U+2029 written as
    ``\uXXXX`` escapes, so the bytes can be embedded in an HTML ``<script>`` element as they are.
    The same document always gives the same bytes.
    """
    return _canonical_bytes(run_data.model_dump(mode="json"))


# --- Rows ------------------------------------------------------------------------------------


def _engine_id(engine: EngineIdentity) -> str:
    return f"{engine.name}|{engine.version}|{engine.model or 'none'}"


def _thermo_id(options: ThermoAnalysisOptions) -> str:
    return (
        f"thermo:{options.imag_tol_cm1!r}:{options.sym_tol_angstrom!r}:"
        f"{options.linear_tol_angstrom!r}:{options.max_automorphisms}"
    )


def _unit_id(candidate_id: str, pathway: str, engine: EngineIdentity) -> str:
    return f"{candidate_id}|{pathway}|{_engine_id(engine)}"


class _Rows:
    """Cached rows read from the store, and the stage keys asked for."""

    def __init__(self, store: ArtifactStore) -> None:
        self.store = store
        self.asked: set[tuple[str, str]] = set()

    def get(self, kind: str, key: str) -> dict[str, Any] | None:
        self.asked.add((kind, key))
        # ``ArtifactStore.get`` looks a row up by ``StageKey.key`` alone (the primary key).
        return self.store.get(
            StageKey(
                key_schema=KEY_SCHEMA,
                geometry_hash="",
                stage_hash="",
                key=key,
                stage_kind=kind,
                engine="",
                engine_version="",
            )
        )


def _final_coordinates(row: dict[str, Any]) -> list[list[float]] | None:
    """Return the converged geometry of an optimization row, or ``None``."""
    if "failed_reason" in row:
        return None
    if "final_state" in row:
        return list(row["final_state"]["coordinates"])
    return list(row["final_xyz"]) if "final_xyz" in row else None


def _frame(frame: OptimizationFrame) -> Frame:
    return Frame(
        coordinates_angstrom=frame.coordinates_angstrom,
        energy_hartree=frame.energy_hartree,
        max_gradient_hartree_per_bohr=frame.max_gradient_hartree_per_bohr,
        accepted_bool=frame.accepted_bool,
        ladder_step=frame.ladder_step,
    )


def _failed_convergence(code: str) -> Convergence:
    return Convergence(
        converged_bool=False,
        failed_code=code,
        n_steps=None,
        n_engine_calls=None,
        final_energy_hartree=None,
        final_max_gradient_hartree_per_bohr=None,
        recovery_steps=[],
    )


def _trajectory_content(
    kind: TrajectoryKind, row: dict[str, Any]
) -> tuple[list[Frame], Convergence]:
    """Return the frames and convergence data of one optimization row."""
    if "failed_reason" in row:
        frames = [_frame(OptimizationFrame.model_validate(f)) for f in row.get("frames", [])]
        return frames, _failed_convergence(str(row["failed_reason"]))
    if kind == "ts_search":
        search = TSSearchResult.model_validate(row)
        frames = [
            Frame(
                coordinates_angstrom=step.coordinates_angstrom,
                energy_hartree=step.energy_hartree,
                max_gradient_hartree_per_bohr=step.max_gradient_hartree_per_bohr,
                accepted_bool=step.accepted_bool,
                ladder_step=None,
            )
            for step in search.history
            if step.coordinates_angstrom is not None  # absent in rows older than v0.7.0
        ]
        return frames, Convergence(
            converged_bool=True,
            failed_code=None,
            n_steps=search.n_steps,
            n_engine_calls=None,
            final_energy_hartree=search.final_energy_hartree,
            final_max_gradient_hartree_per_bohr=search.final_max_gradient_hartree_per_bohr,
            recovery_steps=[],
        )
    frames = [_frame(OptimizationFrame.model_validate(f)) for f in row.get("frames", [])]
    return frames, Convergence(
        converged_bool=True,
        failed_code=None,
        n_steps=row["n_steps"],
        n_engine_calls=row["n_engine_calls"],
        final_energy_hartree=row["final_energy_hartree"],
        final_max_gradient_hartree_per_bohr=None,
        recovery_steps=list(row["recovery_steps"]),
    )


class _Export:
    """The entries collected while walking a record's runs.

    A row referred to twice for the same species is one entry, as the first reference reads it
    (its label and, for a frequency, its geometry).
    """

    def __init__(self, record: RunRecord, store: ArtifactStore) -> None:
        self.rows = _Rows(store)
        self.species: dict[str, RecordSpecies] = _index(
            "species_id", ((s.species_id, s) for s in record.species)
        )
        self.frequencies: dict[str, FrequencyEntry] = {}
        self.trajectories: dict[str, TrajectoryEntry] = {}

    def spec(self, species_id: str) -> RecordSpecies:
        if species_id not in self.species:
            raise ExportError(f"the record has no species {species_id!r}")
        return self.species[species_id]

    def trajectory(self, kind: TrajectoryKind, species_id: str, label: str, key: str) -> str:
        spec = self.spec(species_id)
        stage_kind = {
            "pre_relax": "constrained_preopt",
            "ts_search": "ts_opt",
            "endpoint_opt": "geometry_opt",
        }[kind]
        row = self.rows.get(stage_kind, key)
        trajectory_id = f"{kind}:{species_id}:{key}"
        identity: dict[str, Any] = {
            "trajectory_id": trajectory_id,
            "kind": kind,
            "species_id": species_id,
            "label": label,
            "stage_key": key,
        }
        if row is None:
            entry: TrajectoryEntry = TrajectoryMissing(status="missing", **identity)
        else:
            frames, convergence = _trajectory_content(kind, row)
            n_atoms = len(spec.state.symbols)
            if any(len(f.coordinates_angstrom) != n_atoms for f in frames):
                raise ExportError(f"row {key} does not have the atoms of species {species_id!r}")
            entry = TrajectoryStored(
                status="stored",
                frames=frames,
                n_frames_total=len(frames),
                decimation_stride=1,
                convergence=convergence,
                **identity,
            )
        self.trajectories.setdefault(trajectory_id, entry)
        return trajectory_id

    def frequency(
        self,
        species_id: str,
        key: str,
        analysis: ThermoAnalysisOptions,
        geometry_rows: Sequence[tuple[str, str]],
    ) -> str:
        """Add the frequency entry of ``key``.

        The modes are taken at the full-precision final geometry of the ``geometry_rows``
        optimization whose grid geometry is the frequency row's; without one, at the grid
        geometry the row itself stores.
        """
        spec = self.spec(species_id)
        row = self.rows.get("frequency", key)
        frequency_id = f"frequency:{species_id}:{key}:{_thermo_id(analysis)}"
        identity: dict[str, Any] = {
            "frequency_id": frequency_id,
            "species_id": species_id,
            "stage_key": key,
        }
        entry: FrequencyEntry
        if row is None:
            entry = FrequencyMissing(status="missing", **identity)
        elif "failed_reason" in row:
            entry = FrequencyFailed(
                status="failed", failed_code=str(row["failed_reason"]), **identity
            )
        else:
            geometry = row["geometry"]
            if list(geometry["symbols"]) != list(spec.state.symbols):
                raise ExportError(f"row {key} does not have the atoms of species {species_id!r}")
            grid = [list(r) for r in geometry["coordinates"]]
            coordinates = [[float(x) for x in r] for r in grid]
            for kind, opt_key in geometry_rows:
                opt_row = self.rows.get(kind, opt_key)
                final = None if opt_row is None else _final_coordinates(opt_row)
                if final is not None and [[grid_coordinate(x) for x in r] for r in final] == grid:
                    coordinates = final
                    break
            modes = normal_modes(
                spec.state.symbols,
                coordinates,
                row["hessian_hartree_per_bohr2"],
                analysis=analysis,
            )
            imaginary = []
            for column, frequency in enumerate(modes.frequencies_cm1):
                if frequency < -analysis.imag_tol_cm1:
                    vector = modes.modes_cartesian[:, column]
                    # The eigenvector's sign is arbitrary: fix it, so the bytes are stable.
                    vector = vector * np.sign(vector[np.argmax(np.abs(vector))])
                    imaginary.append(
                        ImaginaryMode(
                            frequency_cm1=frequency,
                            displacements_angstrom=vector.reshape(-1, 3).tolist(),
                        )
                    )
            entry = FrequencyCompleted(
                status="completed",
                coordinates_angstrom=coordinates,
                frequencies_cm1=list(modes.frequencies_cm1),
                n_imaginary=len(imaginary),
                imag_tol_cm1=analysis.imag_tol_cm1,
                imaginary_modes=imaginary,
                **identity,
            )
        self.frequencies.setdefault(frequency_id, entry)
        return frequency_id

    def candidate(self, run: RecordRun, candidate: RecordCandidate, ddg: float | None) -> Candidate:
        """Resolve one run's rows and return its candidate entry."""
        state = self.spec(run.species_id).state
        samples: dict[tuple[str, int], tuple[str | None, list[str]]] = {}
        frequency_ids: list[str] = []
        trajectory_ids: list[str] = []
        for sample in run.samples:
            where = (sample.template_id, sample.sample_index)
            if where in samples:
                raise ExportError(f"duplicate sample {where} in a run")
            label = f"{sample.template_id}:{sample.source}"
            own: list[str] = []
            if sample.pre_relax_key is not None:
                own.append(
                    self.trajectory("pre_relax", sample.species_id, label, sample.pre_relax_key)
                )
            if sample.ts_opt_key is not None:
                own.append(
                    self.trajectory("ts_search", sample.species_id, label, sample.ts_opt_key)
                )
            frequency_id = None
            if sample.frequency_key is not None:
                geometry = [("ts_opt", sample.ts_opt_key)] if sample.ts_opt_key else []
                frequency_id = self.frequency(
                    sample.species_id, sample.frequency_key, run.analysis, geometry
                )
                frequency_ids.append(frequency_id)
            samples[where] = (frequency_id, own)
            trajectory_ids.extend(own)

        endpoint_frequency_ids: list[str] = []
        endpoint_trajectory_ids: list[str] = []
        for endpoint in run.endpoints:
            label = self.spec(endpoint.species_id).label
            endpoint_trajectory_ids.extend(
                self.trajectory("endpoint_opt", endpoint.species_id, label, key)
                for key in endpoint.opt_keys
            )
            geometry = [("geometry_opt", key) for key in endpoint.opt_keys]
            endpoint_frequency_ids.extend(
                self.frequency(endpoint.species_id, key, run.analysis, geometry)
                for key in endpoint.frequency_keys
            )

        fallback = run.fallback
        chosen = fallback.chosen_template_id
        rank = next((a.rank for a in fallback.attempts if a.outcome == "chosen"), None)
        members = []
        for member in run.ensemble.members if run.ensemble else []:
            found = samples.get((chosen or "", member.index))
            if found is None:
                raise ExportError(
                    f"ensemble member {member.index} of template {chosen!r} has no sample"
                )
            members.append(
                Member(
                    member_index=member.index,
                    source=member.source,
                    weight_fraction=member.weight,
                    gibbs_free_energy_hartree=member.G_hartree,
                    degeneracy=member.degeneracy,
                    rmsd_to_seed_angstrom=member.rmsd_to_seed_angstrom,
                    frequency_id=found[0],
                    trajectory_ids=found[1],
                )
            )
        # A grafted template is ``<reference id>__<candidate id>``; records name the reference.
        reference = None if chosen is None else chosen.removesuffix(f"__{candidate.candidate_id}")
        node_records = [r for r in candidate.records if r.node_id == fallback.node_id]
        rmsds = [
            r.alignment_rmsd_angstrom
            for r in node_records
            if r.status == "ok"
            and r.template_id == reference
            and r.alignment_rmsd_angstrom is not None
        ]
        return Candidate(
            candidate_entry_id=_unit_id(run.candidate_id, run.pathway, run.engine),
            candidate_id=run.candidate_id,
            entry_ids_by_site=candidate.entry_ids_by_site,
            pathway=run.pathway,
            node_id=fallback.node_id,
            engine_id=_engine_id(run.engine),
            thermo_options_id=_thermo_id(run.analysis),
            species_id=run.species_id,
            charge=state.charge,
            spin_multiplicity=state.spin_multiplicity,
            template_rank_used=rank,
            chosen_template_id=chosen,
            stop_reason_code=fallback.stop_reason,
            fallback_attempts=[
                FallbackAttemptCode(
                    template_id=a.template_id,
                    rank=a.rank,
                    outcome=a.outcome,
                    reason_code=a.reason,
                )
                for a in fallback.attempts
            ],
            graft_refusals=[
                GraftRefusal(
                    template_id=r.template_id,
                    site_id=r.site_id,
                    entry_id=r.entry_id,
                    reason_code=str(r.reason),
                )
                for r in node_records
                if r.status == "refused"
            ],
            dG_dagger_kcal_mol=run.dG_dagger_kcal_mol,
            ddG_dagger_kcal_mol=ddg,
            graft_rmsd_angstrom=max(rmsds, default=None),
            stall_cap_reached_bool=run.stall_cap_reached_bool,
            members=members,
            frequency_ids=_distinct(frequency_ids),
            trajectory_ids=_distinct(trajectory_ids),
            endpoint_frequency_ids=_distinct(endpoint_frequency_ids),
            endpoint_trajectory_ids=_distinct(endpoint_trajectory_ids),
        )


def _distinct(ids: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(ids))


def _index(name: str, items: Iterable[tuple[Any, Any]]) -> dict[Any, Any]:
    result: dict[Any, Any] = {}
    for key, value in items:
        if key in result:
            raise ExportError(f"duplicate {name} {key!r} in the record")
        result[key] = value
    return result


# --- Decimation ------------------------------------------------------------------------------


def _kept(n_frames: int, stride: int) -> list[int]:
    """Return every ``stride``-th frame index, and the last."""
    return sorted({*range(0, n_frames, stride), n_frames - 1}) if n_frames else []


def _thin(entry: TrajectoryEntry, stride: int) -> TrajectoryEntry:
    if isinstance(entry, TrajectoryMissing):
        return entry
    kept = _kept(len(entry.frames), stride)
    if len(kept) == len(entry.frames):
        return entry
    return entry.model_copy(
        update={"frames": [entry.frames[i] for i in kept], "decimation_stride": stride}
    )


def _size(entries: Sequence[TrajectoryEntry]) -> int:
    return len(_canonical_bytes([e.model_dump(mode="json") for e in entries]))


def _decimate(entries: list[TrajectoryEntry], budget: int) -> list[TrajectoryEntry]:
    """Return ``entries`` at the smallest common stride whose canonical bytes fit ``budget``.

    Raises:
        ExportBudgetError: Keeping only each trajectory's first and last frame still exceeds it.
    """
    stored = [e for e in entries if isinstance(e, TrajectoryStored)]
    longest = max((len(e.frames) for e in stored), default=0)
    # Each frame's bytes, measured once, rule out hopeless strides cheaply.
    sizes = [[len(_canonical_bytes(f.model_dump(mode="json"))) for f in e.frames] for e in stored]
    fixed = _size(
        [
            e.model_copy(update={"frames": []}) if isinstance(e, TrajectoryStored) else e
            for e in entries
        ]
    )
    for stride in range(1, max(longest, 2)):
        estimate = fixed + sum(
            sum(s[i] + 1 for i in _kept(len(s), stride)) - bool(s) for s in sizes
        )
        if estimate > budget + len(str(stride)) * len(stored):
            continue
        thinned = [_thin(e, stride) for e in entries]
        if _size(thinned) <= budget:
            return thinned
    raise ExportBudgetError(
        f"the trajectories do not fit {budget} bytes even with only first and last frames"
    )


# --- The exporter ----------------------------------------------------------------------------


def export_run_data(
    record: RunRecord, store: ArtifactStore, *, trajectory_byte_budget: int | None = None
) -> RunData:
    """Resolve ``record``'s cached rows into one self-contained ``RunData``.

    No engine is called and nothing is written. Entries are ordered by id, so the same record and
    store give the same document.

    Args:
        record: What ran, with the stage keys of its rows.
        store: The store holding the rows; only its file name is exported.
        trajectory_byte_budget: Largest size in bytes of the canonical ``trajectories`` array.
            Above it every trajectory keeps each ``decimation_stride``-th frame and its last,
            with the smallest common stride that fits. ``None`` keeps every frame.

    Returns:
        The document; a row the store lacks is a ``missing`` entry.

    Raises:
        ExportError: The record refers to something it does not declare, declares it twice, or
            a row does not fit its species.
        ExportBudgetError: No decimation fits the budget.
        ValueError: A value the contract refuses (``pydantic.ValidationError``), such as a reason
            that is not a code.
    """
    export = _Export(record, store)
    candidates_by_id = _index("candidate_id", ((c.candidate_id, c) for c in record.candidates))
    gaps: dict[tuple[str, str, str], float] = {}
    for scored in record.selectivity:
        for pathway in scored.result.per_pathway:
            where = (scored.candidate_id, pathway, _engine_id(scored.engine))
            if where in gaps:
                raise ExportError(f"two selectivity results cover {where}")
            gaps[where] = scored.result.ddG_dagger_kcal_mol

    candidates: dict[str, Candidate] = {}
    for run in record.runs:
        unit = _unit_id(run.candidate_id, run.pathway, run.engine)
        if unit in candidates:
            raise ExportError(f"duplicate run {unit!r} in the record")
        if run.candidate_id not in candidates_by_id:
            raise ExportError(f"the record has no candidate {run.candidate_id!r}")
        ddg = gaps.get((run.candidate_id, run.pathway, _engine_id(run.engine)))
        candidates[unit] = export.candidate(run, candidates_by_id[run.candidate_id], ddg)

    def unit_of(ref: RecordUnitRef | None) -> str | None:
        return None if ref is None else _unit_id(ref.candidate_id, ref.pathway, ref.engine)

    gates = _index(
        "gate",
        (
            (
                (unit_of(g.unit_ref) or "", g.gate_id),
                Gate(
                    gate_id=g.gate_id,
                    candidate_entry_id=unit_of(g.unit_ref),
                    pass_bool=g.pass_bool,
                    value=g.value,
                    unit=g.unit,
                    threshold=g.threshold,
                    detail_code=g.detail_code,
                ),
            )
            for g in record.gates
        ),
    )

    trajectories = [export.trajectories[k] for k in sorted(export.trajectories)]
    if trajectory_byte_budget is not None:
        trajectories = _decimate(trajectories, trajectory_byte_budget)

    engines = {_engine_id(r.engine): r.engine for r in record.runs}
    optimizers = {(o.name, o.version) for r in record.runs for o in r.optimizers}
    thermo = {_thermo_id(r.analysis): r.analysis for r in record.runs}
    return RunData(
        schema_version=SCHEMA_VERSION,
        provenance=Provenance(
            eta_version=eta_rxncat.__version__,
            store_file_name=Path(store.path).name,
            engines=[
                EngineEntry(engine_id=i, name=e.name, version=e.version, model=e.model)
                for i, e in sorted(engines.items())
            ],
            optimizers=[OptimizerEntry(name=n, version=v) for n, v in sorted(optimizers)],
            thermo_options=[
                ThermoOptionsEntry(thermo_options_id=i, **o.model_dump())
                for i, o in sorted(thermo.items())
            ],
            stage_keys=[
                StageKeyEntry.model_validate({"stage_kind": kind, "stage_key": key})
                for kind, key in sorted(export.rows.asked)
            ],
        ),
        species=[
            Species(
                species_id=s.species_id,
                label=s.label,
                symbols=s.state.symbols,
                coordinates_angstrom=s.state.coordinates,
                charge=s.state.charge,
                spin_multiplicity=s.state.spin_multiplicity,
                active_atom_indices=s.state.active_atom_indices,
            )
            for _, s in sorted(export.species.items())
        ],
        frequencies=[export.frequencies[k] for k in sorted(export.frequencies)],
        trajectories=trajectories,
        candidates=[candidates[k] for k in sorted(candidates)],
        gates=[gates[k] for k in sorted(gates)],
    )
