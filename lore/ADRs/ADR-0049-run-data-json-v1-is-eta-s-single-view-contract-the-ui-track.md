## Context

TJ asked for a way to audit enumerated TSs by eye (v0.7.0 Q-A3, row `qitem-20261125202813-4331bdd0fedc0322`).
He then said the work should also start eta's user interface in HTML (row
`qitem-20261125203022-a8e19bbeecc4e646`), with this concern: "you have to load up a server for
non-technical, non-savvy scientists, this may be difficult, so it would be better to have a more
user-friendly solution". He chose a placement for the UI track (row
`qitem-20261125203315-64b10106c04fe484`, placement A) and asked for it to be recorded as a proposed
master-plan change, not an edit to `PRDs/`.

## Decision

- **Data/view split.** Every eta run is exported as **run-data JSON**, the single public contract
  every view reads. It has an integer `schema_version` (1 in v0.7.0). Views never read the store,
  the record or anything else.
- **Version rule.**
  - Additive optional keys keep the version and are listed in the schema's `CHANGES`.
  - Removing, renaming or retyping a key, changing a unit or meaning, or adding an enum value bumps
    the version.
  - The writer model is strict (`extra="forbid"`, `Literal[1]`). The reader is lenient: it ignores
    unknown keys and refuses a higher version.
  - The JSON Schema is generated from the model, committed, and drift-tested.
- **Static first.** v0.7.0's review bundle is static and serverless:
  - it opens by double-clicking `index.html`;
  - the data is embedded with the canonical escaped serialisation, byte-equal to `run_data.json`;
  - scripts are classic; there is no `fetch`, and a CSP sets `connect-src 'none'`;
  - a JS-free static summary carries the audit-critical numbers.
- **Reusable components.** eta's own `eta-view.js` (MIT, no build step) provides five components of
  the form `(element, runData, id) -> {update, destroy}`, which later views compose unchanged.
- **Assets.** UI assets are vendored, version-pinned, licence-verified at source and permissive
  only. They are never a core runtime dependency. 3Dmol.js 2.5.5 (BSD-3) is the first.
- **Proposed master-plan changes, for TJ's edit:**
  1. v0.7.0 adds the static review bundle.
  2. v0.8.0 adds a read-only network view over run-data.
  3. v0.9.0 adds conformer, frequency and topology views.
  4. v1.1.0 is the interactive `eta ui`: a local backend, network editing, and graft-atom selection
     exporting `ReactionGraph`.
  5. v1.2.0 is desktop packaging (pywebview recommended; final choice later).
  6. Known Constraints gains the asset rule above.

## Consequences

- TJ's scripts and every later view depend on one versioned document, so the planned v1.0 API
  freeze has a contract to freeze.
- Static bundles cost duplicated bytes (the file plus the embedded copy). Frames are decimated in
  the data (`decimation_stride`, `n_frames_total`), never silently.
- JS rendering is not CI-tested. A recorded browser smoke with known answers and TJ's own audit are
  its checks, and the static summary keeps the audit from resting on JS alone.
