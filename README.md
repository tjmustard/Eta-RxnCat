<div align="center">
    <img src="./media/icons/web/icon-256.webp" alt="Eta-RxnCat logo" width="200" height="200"/>
    <h1>Eta-RxnCat</h1>
    <h3><em>Priority-gated reaction-graph workflows for homogeneous catalysis, built on a permissively licensed core.</em></h3>
</div>

<p align="center"><img src="./media/banner/banner-1024x573.webp" alt="Eta-RxnCat banner" width="100%"/></p>

<p align="center">
    <strong>Eta-RxnCat is a computational-chemistry library for mapping organometallic and organocatalytic reaction mechanisms. A reaction is written once as a graph of states and transition states, every molecule carries an explicit charge and spin multiplicity, and each computational stage is cached on its own so a run can resume and extend. Version 0.2.0 adds the energy engines: RDKit force fields, PySCF / GPU4PySCF DFT on CPU or GPU, GFN2-xTB as a subprocess, and the MACE, UMA and eSEN machine-learned potentials, each honouring charge and spin exactly or refusing. Version 0.3.0 adds conformer search, ground-state optimisation, quasi-RRHO thermochemistry at a 1 M standard state, Boltzmann ensembles and a cached single-species stage runner. Version 0.4.0 adds a conserved-core structure mapper, which aligns a fragment onto a known transition state, grafts it in with explicit charge and spin, and pre-relaxes the result with the core frozen to give a guess for a new transition state. Version 0.5.0 turns that guess into a transition state: a P-RFO saddle-point search, an active-core frequency validator and activation free energies.</strong>
</p>

<p align="center">
    <a href="https://github.com/tjmustard/Eta-RxnCat/releases/latest"><img src="https://img.shields.io/badge/release-v0.5.0-blue" alt="Latest Release"/></a>
    <a href="https://github.com/tjmustard/Eta-RxnCat/actions/workflows/ci.yml"><img src="https://github.com/tjmustard/Eta-RxnCat/actions/workflows/ci.yml/badge.svg" alt="CI"/></a>
    <a href="https://github.com/tjmustard/Eta-RxnCat/stargazers"><img src="https://img.shields.io/github/stars/tjmustard/Eta-RxnCat?style=social" alt="GitHub stars"/></a>
    <a href="https://github.com/tjmustard/Eta-RxnCat/blob/main/LICENSE"><img src="https://img.shields.io/github/license/tjmustard/Eta-RxnCat" alt="License"/></a>
</p>

---

## Table of Contents

- [🔬 What is Eta-RxnCat?](#-what-is-eta-rxncat)
- [✨ Features (v0.5.0)](#-features-v050)
- [⚡ Installation](#-installation)
- [🚀 Usage](#-usage)
- [🧪 Development](#-development)
- [🧭 Roadmap](#-roadmap)
- [🙏 Acknowledgements](#-acknowledgements)
- [📄 License](#-license)

## 🔬 What is Eta-RxnCat?

Eta-RxnCat describes a catalytic mechanism as a **reaction graph**. Nodes are reactants,
intermediates, transition states, products and off-cycle sinks. Each node holds one or more ranked
template geometries, and edges are the elementary steps between nodes (catalytic cycles are
allowed). Nodes carry a priority tier, so the most informative steps, such as a
selectivity-determining transition state, can be computed first and used to prune the rest.

The long-term goal, set out in the living master plan, is a workflow that combines force fields,
subprocess-isolated tight binding, machine-learned potentials and DFT (PySCF / GPU4PySCF) under
that priority-gated graph. `v0.1.0` built the foundation; `v0.2.0` added the engines that compute
energies, forces and Hessians on it; `v0.3.0` turns one species into a Boltzmann ensemble of
optimised conformers with free energies, and combines species into reaction free energies;
`v0.4.0` maps a fragment onto the conserved core of a known transition state to build a guess
for a new one; `v0.5.0` optimises that guess to a validated transition state and computes its
activation free energy. Everything beyond it is listed under [Roadmap](#-roadmap) and is not built yet.

## ✨ Features (v0.5.0)

- **Strict core data contracts** (`eta_rxncat.core`). Pydantic v2 models reject unknown keys and
  are immutable. Charge, spin multiplicity, counts, ranks and atom indices are strict integers
  (`True`, `"1"` and `1.0` are rejected). Every `MolecularState` must have a canonical element
  symbol per atom (Z 1–118), finite N×3 coordinates, and a charge and multiplicity its electron
  count allows.
- **Reaction-graph loader and validator.** `load_reaction_graph` reads YAML or JSON and rejects
  duplicate keys. Every failure is one `GraphValidationError` that names the offending file, key,
  node, template, edge or rule. The graph checks cover unique ids, known edge endpoints, no
  self-loops or duplicate edges, defined pruning-rule references, atom-mapping invariants, and
  equal charge and element composition across a node's templates.
- **Stage cache key and artifact store** (`eta_rxncat.store`). Each stage gets a versioned,
  canonical SHA-256 key built from the geometry (5-decimal grid), the stage settings and the
  engine identity. A WAL-mode SQLite store never silently overwrites a completed artifact:
  `invalidate` is the only way to replace one.
- **Hardware probe and GPU smoke test** (`eta_rxncat.utils.hw_probe`). A typed report of
  PyTorch/CUDA, the GPU, GPU4PySCF and a 6.5 GiB VRAM budget, which never raises for a missing or
  broken package. The smoke test compares GPU4PySCF with CPU PySCF and a CUDA matmul with the CPU
  result, against fixed numeric tolerances. Without CUDA it reports `skipped`. GPU acceptance
  passed on 2026-11-23 on an NVIDIA GeForce RTX 5060 Ti (compute capability 12.0, PyTorch
  2.13.0+cu129), with GPU4PySCF and CPU PySCF agreeing to |ΔE| ≈ 1e-12 Eh in the smoke test and
  every engine accepted on this host (see
  [GPU_SMOKE_RESULT.json](docs/prd/v0.2.0/GPU_SMOKE_RESULT.json)).
- **Command line**: `eta-rxncat validate` and `eta-rxncat hardware-check [--smoke]`, with a fixed
  exit-code table and one-line errors.
- **Optional extras** `gpu` (GPU4PySCF, CuPy, PyTorch), `mlip-mace` (the `mace` engine) and
  `mlip-uma` (the `uma_direct` and `esen_omol25` engines), and a per-environment **licence gate**
  (`tools/licence_gate.py`).

### Engines (v0.2.0)

- **One engine contract** (`eta_rxncat.engines`). Every engine is built from a stage with
  `from_stage`. Its resolved stage holds every keyed option (given or default) plus
  `engine_impl`, and is what the stage cache key is built from. The device is never keyed.
  Results are a `PotentialResult`: energy (Eh), forces (Eh/Bohr) and an optional Hessian
  (Eh/Bohr², `analytic` or `finite_difference`), with the device, the reason for it, and the
  recovery steps taken. Units are CODATA 2018. Failures are typed (`EngineInputError`,
  `EngineUnavailableError`, `ScfConvergenceError`, `EngineRuntimeError`).
- **Charge and spin are honoured exactly, or refused.** An engine that cannot represent a state
  raises `EngineInputError` naming the engine, charge and multiplicity. It never silently
  computes something else.
- **Six engines**:
  - `rdkit_ff`: RDKit UFF and MMFF94, neutral singlets only;
  - `pyscf_gpu_cpu`: PySCF RKS/UKS/RHF/UHF (density-fitted by default) on the CPU, or GPU4PySCF on CUDA. It
    applies the def2 ECP rule, ddCOSMO and C-PCM/IEF-PCM solvation, an SCF escalation ladder and a
    mandatory internal stability analysis. The stability threshold is keyed and robust to
    threaded-CPU noise. On CUDA, a stage over the VRAM budget, or one that hits a listed
    out-of-memory error, runs on the CPU instead, with the reason recorded. A GPU KS analytic
    Hessian is used only where the committed support record shows it correct; elsewhere the
    Hessian is a finite difference of analytic gradients. Across the four test cases, GPU energies
    match CPU to ≤ 2e-7 Eh;
  - `xtb_subprocess`: GFN2-xTB 6.8.0 as a separate process (LGPL-3.0, never in-process), with a
    Hessian from finite differences of its gradients;
  - `mace`: MACE-MP-0 medium, neutral singlets only, with the model file pinned by SHA-256;
  - `uma_direct` and `esen_omol25`: fairchem's UMA (`uma-s-1p2p1`) and eSEN OMol25 models at high
    precision, with charge and spin passed through. They match fairchem's own predictor to
    ≤ 3e-8 Eh on the four test cases.
- **Known limits** are listed in the record's `known_limits`. One affects users: `import mace`
  sets `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1` for the whole process, so keep the `mlip-mace` and
  `mlip-uma` environments separate (they are mutually exclusive extras anyway).

### Conformers, optimisation and ensembles (v0.3.0)

- **Thermochemistry** (`eta_rxncat.thermo`). Ideal-gas quasi-RRHO (Grimme 2012) at a 1 M standard
  state, from a Cartesian Hessian: Eckart-projected normal modes (nothing dropped by magnitude;
  soft modes listed), a rotational symmetry number from the geometry and its graph automorphisms,
  RDKit masses for Z 1–118, and log-sum-exp Boltzmann weights with degeneracies. A ground state
  with an imaginary mode raises `NotAMinimumError`.
- **Optimizer interface** (`eta_rxncat.optimize`). `GeometricOptimizer` runs geomeTRIC 1.1.1
  through its lower-level API in a temporary directory, without touching the host's logging, and
  records a three-step recovery ladder (`tric`, `tric_tight_trust`, then `cartesian`, or `hdlc`
  under dihedral constraints). geomeTRIC is the optional `opt-geometric` extra, no longer a core
  dependency.
- **Conformers** (`eta_rxncat.conformers`). Two ETKDGv3 passes from a SMILES (the second without
  experimental torsion preferences, so the s-cis-side class of a diene is sampled), optional
  stereo-checked seed geometries, dedup by proper-rotation RMSD over graph automorphisms, an
  energy window and a per-conformer mirror degeneracy. Isotope labels are refused.
- **Single-species stage runner** (`eta_rxncat.orchestrator`). `run_species` runs conformer
  search, optimisation, frequencies (with at most one imaginary-mode push, then a re-dedup) and
  any extra single points, each stage cached in the v0.1.0 artifact store, so a rerun or an added
  solvation single point reuses every earlier stage. `reaction_free_energy` gives ΔE, ΔH,
  ΔG(1 atm) and ΔG(1 M); reports are deterministic JSON.
- The v0.3.0 acceptance record
  ([ACCEPTANCE_RESULT.json](docs/prd/v0.3.0/ACCEPTANCE_RESULT.json)) passed: conformer
  ensembles, quasi-RRHO 1 M thermochemistry and the cached single-species stage runner ran end to
  end on Human Fixtures 1 and 2 and TJ's Tiers 1 and 2, with both the xtb (GFN2) and UMA recipes,
  and every result matched the fixtures TJ promoted.
- With UMA, the n-butane gauche–anti ΔG and the Diels–Alder ΔG_r agree with TJ's
  ωB97M-V/def2-TZVPD//B3LYP/6-31G** reference values within the gated bounds; GFN2's deviations
  are reported, not gated.
- TJ confirmed the derived SMILES of the four Tier 1 and 2 species.
- UMA's Tier 2 ΔG_r(1 M) lies inside TJ's −42 to −20 kcal/mol window; GFN2's lies outside it and is
  reported, not gated.

### Conserved-core mapper (v0.4.0)

- **Graft contracts** (`eta_rxncat.core`). `GraftSpec` holds the template's keep, delete and
  alignment lists (ADR-0005), the ordered fragment atoms paired with them, an optional
  `fragment_delete` list, an optional constrained core, and the product's charge and
  multiplicity, which are always given and never inferred. `GraftResult` carries the product, the
  source of every product atom, the alignment RMSD, the close contacts, the junction signed
  volumes and a planar-pair-set flag.
- **Alignment** (`eta_rxncat.mapping.superpose`). Horn quaternion superposition of ordered atom
  pairs. It never reflects (det R = +1), computes the RMSD from the residuals, and refuses fewer
  than three pairs, collinear pair sets and rotations that are not unique (`AlignmentError`).
- **Graft surgery** (`eta_rxncat.mapping.graft`). The product lists the kept template atoms first,
  with their coordinates copied bit for bit, then the fragment atoms that are neither paired nor
  deleted. Paired fragment atoms are always dropped. Atoms closer than 0.5 Å raise
  `GraftClashError`. Close contacts and the handedness across each new bond are recorded rather
  than refused, so nothing about a graft is silent.
- **Core-frozen pre-relaxation** (`eta_rxncat.mapping.relax_constrained_core`). It runs the
  v0.3.0 `Optimizer` with the core atoms frozen and raises `CoreDisplacementError` if a core atom
  moves more than 1e-6 Å. The result is a transition-state guess, not a minimum.
- **Clean room.** The mapper was written from an approved behaviour specification, not from the
  original `nMap` code, whose copyright is shared with Oregon State University, the author's
  advisor and his co-authors. Checker-approved test vectors from that specification are part of the test suite.
- The v0.4.0 acceptance record
  ([ACCEPTANCE_RESULT.json](docs/prd/v0.4.0/ACCEPTANCE_RESULT.json)) passed: the conserved-core
  mapper (quaternion alignment, ordered graft surgery with explicit charge/spin, core-frozen
  pre-relaxation) ran TJ's Fixture M1 end to end with both the xtb (GFN2) and UMA recipes, and
  every result matched the fixtures TJ promoted.
- TJ's Fixture M1 grafts within the 0.10 Å forming-core bound and pre-relaxes on the xtb (GFN2)
  and UMA recipes with TS1b_n's connectivity and junction handedness.
- TJ confirmed the M1 atom map by promoting the graft.

### Transition-state search and validation (v0.5.0)

- The v0.5.0 acceptance record
  ([ACCEPTANCE_RESULT.json](docs/prd/v0.5.0/ACCEPTANCE_RESULT.json)) passed: P-RFO
  transition-state search, an active-core frequency validator and transition-state barriers ran
  TJ's five Tier 3 transition states with both the xtb (GFN2) and UMA recipes, and every gated
  result matched the fixtures TJ promoted.
- With UMA, all five transition states pass every gate: convergence, one imaginary mode, the
  active core, the TS identity and TJ's ΔG‡(1 M) window, and ΔG‡(TS4a) < ΔG‡(TS3a).
- With GFN2, TS1a_n, TS1b_n, TS3a and N4 pass convergence, the mode count and the identity core
  (forming-bond overlap ≥ 0.50, in phase, active-core KE ≥ 0.60); GFN2 TS4a is report-only by
  TJ's decision.
- TJ's regression bounds: |ΔE_TS| ≤ 1e-5 Eh, heavy-atom RMSD ≤ 0.01 Å, |ΔΔG‡(1 M)| ≤ 0.75
  kcal/mol on UMA and ≤ 0.01 kcal/mol on GFN2.
- A geomeTRIC black-box cross-check ran on every case and recipe; it is reported, not gated.
- The six new Tier 3 structures match their recorded sha256s and reproduce Liu's energies within
  1e-4 Eh where Liu prints one; TJ confirmed the transcriptions.

## ⚡ Installation

Eta-RxnCat uses [`uv`](https://docs.astral.sh/uv/) and supports Python 3.11–3.13 (the lock
targets 3.12).

```bash
git clone https://github.com/tjmustard/Eta-RxnCat.git
cd Eta-RxnCat
uv sync          # core install from the committed uv.lock
uv run pytest    # run the test suite
```

Optional extras, each installed from the lock:

```bash
uv sync --extra gpu                       # PyTorch (CUDA 12.9 wheels), GPU4PySCF, CuPy
uv sync --extra gpu --extra mlip-mace     # adds MACE (mace-torch)
uv sync --extra gpu --extra mlip-uma      # adds UMA (fairchem-core)
uv sync --extra opt-geometric             # geomeTRIC 1.1.1 for GeometricOptimizer
```

`mlip-mace` and `mlip-uma` are **mutually exclusive**: they need incompatible `e3nn` versions, so
one environment holds one MLIP at a time, and `uv` refuses to install both.

> **Note:** some engines need files that `uv` does not install, and no engine downloads them
> itself. `xtb_subprocess` needs the xtb 6.8.0 binary (its `binary` argument, `ETA_RXNCAT_XTB`
> or `PATH`). `mace` needs the MACE-MP-0 medium model file (`model_path`), and its SHA-256 must
> match the pin. `uma_direct` and `esen_omol25` need fairchem's weights, which are gated on
> Hugging Face (fairchem's cache or `checkpoint_path`). Versions, sources and digests are in
> [`docs/licence-inventory.md`](docs/licence-inventory.md).

## 🚀 Usage

Validate a reaction graph:

```console
$ uv run eta-rxncat validate tests/data/reaction_graphs/example_reaction_graph.yaml
OK tests/data/reaction_graphs/example_reaction_graph.yaml
nodes: 3
edges: 2
priority_order: ts_sn2,products,reactants
```

An invalid graph prints one line on stderr and exits 1:

```console
$ printf 'schema_version: 1\nname: empty\nnodes: []\n' > empty.yaml
$ uv run eta-rxncat validate empty.yaml
error: empty.yaml: nodes: List should have at least 1 item after validation, not 0
```

Report the hardware as JSON (exit 0; problems appear in `flags`). On a core install without the
`gpu` extra:

```console
$ uv run eta-rxncat hardware-check
{
  "report_schema": 1,
  "python_version": "3.12.16",
  "platform": "Linux-…",
  "torch": {
    "installed": false,
    "version": null,
    "cuda_available": false,
    "cuda_version": null
  },
  "gpu": null,
  …
  "flags": [
    "torch_missing",
    "cuda_unavailable",
    "gpu4pyscf_missing"
  ],
  …
}
```

Run the GPU smoke test. It exits 0 on a pass, 1 on a failure and 3 when it is skipped because
PyTorch, CUDA or GPU4PySCF is not available:

```console
$ uv run eta-rxncat hardware-check --smoke
{
  "result_schema": 1,
  "status": "skipped",
  "reason": "torch is not installed; gpu4pyscf is not installed",
  "scf": null,
  "torch_op": null,
  …
}
```

| Command | Exit 0 | Exit 1 | Exit 2 | Exit 3 |
|---|---|---|---|---|
| `hardware-check` | report printed | — | usage error | — |
| `hardware-check --smoke` | smoke pass | smoke fail | usage error | skipped |
| `validate <path>` | valid | invalid, unreadable or unsupported file | usage error | — |

`python -m eta_rxncat` is the same command line.

## 🧪 Development

Every change must pass the four gates and the base licence gate:

```bash
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
UV_PROJECT_ENVIRONMENT=.venv-runtime uv sync --locked --no-dev && .venv-runtime/bin/python -I tools/licence_gate.py --profile base
```

CI also runs the licence gate for each optional extra:

```bash
UV_PROJECT_ENVIRONMENT=.venv-runtime uv sync --locked --no-dev --extra opt-geometric && .venv-runtime/bin/python -I tools/licence_gate.py --profile opt-geometric
UV_PROJECT_ENVIRONMENT=.venv-runtime uv sync --locked --no-dev --extra gpu && .venv-runtime/bin/python -I tools/licence_gate.py --profile gpu
UV_PROJECT_ENVIRONMENT=.venv-runtime uv sync --locked --no-dev --extra gpu --extra mlip-mace && .venv-runtime/bin/python -I tools/licence_gate.py --profile mlip-mace
UV_PROJECT_ENVIRONMENT=.venv-runtime uv sync --locked --no-dev --extra gpu --extra mlip-uma && .venv-runtime/bin/python -I tools/licence_gate.py --profile mlip-uma
```

The gate judges every installed package from its exact licence metadata (SPDX expression,
classifiers or licence field), with no substring matching. GPU tests live under `tests/gpu/`
behind the `gpu` marker and are skipped by default, as are the end-to-end fixture runs under
`tests/e2e/` (`e2e` marker). Contributor and agent rules are in
`AGENTS.md`.

## 🧭 Roadmap

### Built

- **v0.1.0**: the foundation: data contracts, the reaction-graph loader, the stage artifact
  store, the hardware probe and the command line.
- **v0.2.0**: potentials and engines (RDKit force fields, PySCF / GPU4PySCF, xtb as a subprocess,
  MACE, UMA and eSEN).
- **v0.3.0**: conformer generation, ground-state optimisation and Boltzmann ensembles.
- **v0.4.0**: the conserved-core structure mapper (a clean-room rewrite of `nMap`).
- **v0.5.0**: transition-state optimisation, seeded from the mapper's guess, and an active-core
  frequency validator.

### Planned, not yet built

The full plan is `PRDs/Eta-RxnCat_Living_Master_Plan.md`.

- **v0.6.0**: selectivity branching and competing transition-state screening.
- **v0.7.0**: combinatorial library enumeration and multi-template fallback.
- **v0.8.0**: the full catalytic-cycle orchestrator and the energetic span model.
- **v0.9.0**: covalent topology audit, summary reporting and an end-to-end fixture harness.
- **v1.0.0**: the production command line, an engine registry and documentation.

## 🙏 Acknowledgements

Eta-RxnCat is a clean-room rewrite inspired by:

- **The conserved-core transition-state model and `nMap`.** Mustard, T. J. L.; Wender, P. A.;
  Cheong, P. H.-Y. *ACS Catal.* **2015**, *5*, 1758–1763. DOI:
  [`10.1021/cs501828e`](https://doi.org/10.1021/cs501828e). The geometry of the bond-forming and
  bond-breaking atoms in catalytic transition states stays nearly invariant across diverse
  catalysts, so new catalysts and substrates can be mapped onto conserved cores.
- **[`Eta_Scripts`](https://github.com/tjmustard/Eta_Scripts)**, the original Eta code (tools for
  enhancing the efficiency of computational chemistry workflows), which with `nMap` pioneered
  Kabsch/quaternion subgraph alignment and ordered atom surgery (`keep`, `delete` and `alignment`
  atom lists).
- **The thesis where that code is also published.** Mustard, T. J. L. *Computational
  Investigations of Transition Metal Catalyses and Amorphous Metal Oxides: Accelerating Scientific
  Discovery Through Automation.* Ph.D. dissertation, Chemistry, Oregon State University, 2015.
  [ScholarsArchive@OSU](https://ir.library.oregonstate.edu/concern/graduate_thesis_or_dissertations/xp68kn058).

## 📄 License

The Eta-RxnCat core is released under the MIT licence (see `LICENSE`).

- **MIT core.** The code in this repository, and every package the core install depends on, is
  MIT, BSD or an equivalent permissive licence. Every core dependency must resolve to an SPDX id on
  the allow-list in `pyproject.toml` (`MIT`, `BSD`, `Apache-2.0`, `ISC`, `PSF`, `Zlib`, `CC0-1.0`,
  `BSL-1.0` and close variants). Since v0.3.0 the core install has no exception: `geometric`
  1.1.1 (BSD 3-clause Non-AI) moved to the optional `opt-geometric` extra, with a version-pinned
  exemption there.
- **Copyleft only in optional engine extras.** The optional engine extras (`gpu`, `mlip-mace`,
  `mlip-uma`) may pull in NVIDIA CUDA wheels and copyleft or off-list packages, such as `ase`. You
  download these yourself when you install an extra. Each one is a version-pinned, per-extra
  exemption. Engines like these can be replaced by a new engine later, but the core stays
  permissive.
- **External programs and model weights** are downloaded by the user and never shipped: the xtb
  binary (LGPL-3.0, run only as a separate process), the MACE-MP-0 weights (MIT), and the UMA and
  OMol25 eSEN weights (FAIR Chemistry License v1, gated). Each is listed in
  `docs/licence-inventory.md` with the decision that allows it.
- **Nothing copyleft in the repository.** Eta-RxnCat never vendors, copies or imports copyleft
  code. Tests enforce this.

Copyright (c) 2026 Thomas J. L. Mustard Ph.D.
