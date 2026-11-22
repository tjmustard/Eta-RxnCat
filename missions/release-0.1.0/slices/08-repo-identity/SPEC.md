---
id: OPR.0.1.0.8
slice: 08-repo-identity
mission: release-0.1.0
status: active
stage: wip
verified: "2026-11-22 against scaffold (hyper_scope slice create)"
created: "2026-11-22"
intent: "Give the repo the sibling-project public face (logo and banner README, Keep a Changelog CHANGELOG, media/) and the author form Thomas J. L. Mustard Ph.D. everywhere the project writes an author, with a filesystem test that blocks any other form; the README claims only what v0.1.0 builds."
depends_on: [OPR.0.1.0.1, OPR.0.1.0.2, OPR.0.1.0.3, OPR.0.1.0.4, OPR.0.1.0.5, OPR.0.1.0.6]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_scaffold
parent: null
hacf_touches: [README.md, CHANGELOG.md, LICENSE, pyproject.toml, uv.lock, "media/**", AGENTS.md, src/eta_rxncat/__init__.py, tests/unit/test_identity.py, docs/prd/v0.1.0/DISCREPANCIES.md, spec/compiled/architecture.yml]
hacf_oracle: [[python3, "-c", "import hashlib,sys;h=lambda p:hashlib.sha256(open(p,'rb').read()).hexdigest();sys.exit(0 if h('media/logo.png')=='3b2a0b7680a59156097f2faa15195eecbb162c4816884a38a28260f50dda527e' and h('media/banner.webp')=='cc3fe67b17ea6e75358f9461623af2a814b75d2d724cb8842b11d751c8e9290f' else 1)"], [uv, run, ruff, check, .], [uv, run, ruff, format, "--check", .], [uv, run, mypy], [uv, run, pytest], [uv, run, pytest, tests/unit/test_identity.py]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Repo identity: README, CHANGELOG, author name and media

## Intent

Give the repo the same public face as TJ's sibling projects:
- a README with the logo and banner;
- a Keep a Changelog `CHANGELOG.md`;
- the author written as **"Thomas J. L. Mustard Ph.D."** everywhere this project writes an
  author, with a deterministic test that stops any other form from coming back.

The README describes only what v0.1.0 actually builds.

Context the builder needs (self-contained). TJ, verbatim (via advisor-lead@kernel, row
`qitem-20261122123807-a377da3572ef57f8`): "Additionally I want a README and CHANGELOG like HACF,
OIN-SMILES, and eta-skills. Here is an image to use as the icon in the README. Also let's ensure
the author says "Thomas J. L. Mustard Ph.D." In the README, LICENSE, and everywhere else." On the
banner, TJ said: "Add this to the repo as well beside the icon. And if it is needed in the README."

Model the README on these sibling READMEs (read-only, structure and tone only; copy no text):
- `~/AI/Hypergraph-Coding-Agent-Framework/README.md`
- `~/Documents/GitHub/OIN-SMILES/README.md`
- `~/Documents/GitHub/eta-skills/README.md`

Model the CHANGELOG on `~/Documents/GitHub/OIN-SMILES/CHANGELOG.md`.

Slice 01 already wrote `README.md` (US-010: the nMap citation, the `Eta_Scripts` credit, a
licensing section and a `uv` quickstart) and `pyproject.toml`. This slice rewrites the README to
the sibling pattern and keeps every slice-01 README requirement. The repo-local git author is
already set by the lead, so there is nothing to do here for git. Node `eta_rxncat_scaffold` owns
the README, docs and pyproject (slice 01). If `media/**`, `CHANGELOG.md`, `LICENSE` or
`tests/unit/test_identity.py` fall outside its `files:`, add them through `hyper_ledger.py
ensure-node --id eta_rxncat_scaffold --files <the full existing list plus these>` (`--files`
replaces the list, so pass the whole list). Never hand-edit `architecture.yml`.

## 1. The Confidence Mandate

**Score: 9/10.** The files, the name form, the media bytes and the guard are fixed. The residual
is README prose quality, which is a judgement call. The proof checks structure and accuracy, not
style.

## Mini-requirements

1. Media. Copy both files byte for byte, and verify each with `sha256sum`:
   - `~/.hacf/eta-rxncat-hacf/incoming/media/logo.png` → `media/logo.png`. 1024×1024 RGBA,
     already cropped with a transparent background. sha256
     `3b2a0b7680a59156097f2faa15195eecbb162c4816884a38a28260f50dda527e`.
   - `~/.hacf/eta-rxncat-hacf/incoming/media/banner.webp` → `media/banner.webp`. 2576×1439,
     279188 bytes. This is TJ's final banner (13:05Z, corrected chemistry panel; it says "Eta-RxnCat", with the full tagline and the eta/cat icon).
     sha256 `cc3fe67b17ea6e75358f9461623af2a814b75d2d724cb8842b11d751c8e9290f`.
   
   No other media files are added. In particular, `banner-original.jpg`, `logo.webp` and every
   superseded `old-*` file (e.g. `old-catalysis-engine-banner.*`, `old-sn2-attempt-banner.jpg`) stay out of the repo.
2. `README.md`, in the sibling pattern:
   1. A centered header `<div align="center">` containing:
      - `<img src="./media/logo.png" alt="Eta-RxnCat logo" width="200" height="200"/>`;
      - `<h1>Eta-RxnCat</h1>`;
      - an italic one-line tagline in `<h3><em>…</em></h3>`.
   2. The banner as a hero image directly below the header:
      `<p align="center"><img src="./media/banner.webp" alt="Eta-RxnCat banner" width="100%"/></p>`.
      The README's own title and tagline say "Eta-RxnCat".
   3. A bold, one-paragraph pitch in `<p align="center"><strong>…</strong></p>`.
   4. A badge row for `github.com/tjmustard/Eta-RxnCat`:
      - release: a static shields badge `release-v0.1.0-blue` linking to `/releases/latest`;
      - CI: the actions badge for `.github/workflows/ci.yml`;
      - stars: `img.shields.io/github/stars/…?style=social`;
      - license: `img.shields.io/github/license/…`.
   5. A `---` rule, then `## Table of Contents` with anchor links that resolve to the headings.
   6. Emoji-prefixed `##` sections, in this order:
      - What is Eta-RxnCat?
      - Features (v0.1.0)
      - Installation (`uv`, including the optional extras `gpu`, `mlip-mace`, `mlip-uma`, and
        the note that the two MLIP extras are mutually exclusive)
      - Usage (`eta-rxncat validate …` and `eta-rxncat hardware-check [--smoke]`, with real
        output shapes)
      - Development (the four gates and the licence gates, as written in `AGENTS.md`)
      - Roadmap (versions v0.2.0 … v1.0.0, one line each, under the heading text "Planned, not
        yet built", pointing to `PRDs/Eta-RxnCat_Living_Master_Plan.md`)
      - Acknowledgements (the nMap citation with DOI `10.1021/cs501828e`, and `Eta_Scripts`)
      - License (MIT; the allow-list and per-extra exemptions in one sentence each;
        `Copyright (c) 2026 Thomas J. L. Mustard Ph.D.`)
   7. Accuracy rule. Every feature, command, flag and output in "Features" and "Usage" must exist
      in the tree at this slice's HEAD, and each Usage example must reproduce. Nothing from
      v0.2.0 onward appears outside "Roadmap". No GPU pass result is claimed, because slice 07
      records it after this slice.
3. `CHANGELOG.md`:
   - The header is `# Changelog`, followed by one line citing
     [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/) and
     [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
   - Then `## [Unreleased]` with `### Added`, holding one bullet per v0.1.0 capability built in
     slices 01–06:
     - scaffold and gates;
     - licence gates;
     - core models and graph loader;
     - cache key and artifact store;
     - hardware probe and smoke;
     - CLI;
     - optional extras.
   - Then `### Changed` with one bullet: "Author name standardised to Thomas J. L. Mustard Ph.D.".
   - There are no version sections or compare links yet, because no tag exists. Upkeep belongs
     to the scribe (the docs+commit step). At each release it renames `[Unreleased]` to
     `## [X.Y.Z] - YYYY-MM-DD`, opens a new `[Unreleased]`, and adds that release's entries. The
     scribe does this from v0.1.0 through v1.0.0. Say so in one line in the `AGENTS.md` project
     section.
4. Author name. The exact form is `Thomas J. L. Mustard Ph.D.`:
   - `LICENSE` line 3 becomes `Copyright (c) 2026 Thomas J. L. Mustard Ph.D.`. The rest of the
     MIT text is unchanged.
   - `pyproject.toml` `[project] authors = [{ name = "Thomas J. L. Mustard Ph.D." }]`, with no
     email.
   - The README License section and any author line in `src/eta_rxncat/__init__.py` (if one
     exists) use the same form.
   - No `CITATION.cff` in v0.1.0 (not asked for).
   - Bibliographic citations of TJ's papers keep the journal's surname-first form (e.g.
     "Mustard, Wender & Cheong"). That form is a citation, not an author line.
5. The guard is `tests/unit/test_identity.py`, a pure-filesystem test. It calls no `git` and uses
   no network.
   - It scans `README.md`, `CHANGELOG.md`, `LICENSE`, `pyproject.toml`, every file under `src/`
     and `tests/`, `docs/**` excluding `docs/prd/**`, `.github/**`, and the part of `AGENTS.md`
     after the HACF END marker.
   - It never reads `PRDs/`, `.agents/`, `.claude/`, `CLAUDE.md`, `HACF-uninstall.sh`, the HACF
     block of `AGENTS.md`, `docs/prd/**` (verbatim reference copies), `missions/`, `lore/` or
     `spec/`.
   - It finds every match of the regex
     `(?:Thomas|Tom|TJ|T\.)(?:\s+[A-Z]\.)*\s+Mustard(?:,?\s*Ph\.?\s*D\.?)?` and fails, naming the
     file, line and text, unless the match is exactly `Thomas J. L. Mustard Ph.D.`.
   - The test assembles its own pattern and canonical string so that it does not flag itself.
   - It also asserts that `LICENSE`, `README.md` and `pyproject.toml` each contain the canonical
     form at least once.
   - The scanner is a function `find_author_violations(root: Path, paths: Iterable[Path]) ->
     list[str]`, tested on `tmp_path` files.
6. US-011 (scaffold area): `docs/prd/v0.1.0/DISCREPANCIES.md` gains these rows, each with status
   `open`:
   - `changed` rows for README structure and for LICENSE and `pyproject` authors, versus the
     starter;
   - `added` rows for `CHANGELOG.md`, `media/logo.png`, `media/banner.webp` and
     `tests/unit/test_identity.py`.

## 3. Implementation Plan (Task List)

- [ ] Task 1: copy and verify the media files (Mini-requirement 1).
- [ ] Task 2: fix the LICENSE and `pyproject` authors; run `uv lock --check` (the metadata change
  must not change the lock; if it does, run `uv lock` and note it).
- [ ] Task 3: write the guard test and its `tmp_path` unit tests; see them fail on the old LICENSE
  form, then pass.
- [ ] Task 4: rewrite the README (Mini-requirement 2) and run every Usage example to confirm it
  reproduces.
- [ ] Task 5: write the CHANGELOG and the one-line scribe rule in `AGENTS.md`.
- [ ] Task 6: add the register rows; run the four gates.

## 4. The Negative Space (Constraints)

- **DO NOT** describe in Features or Usage anything that is not built at this HEAD, or claim a GPU
  pass.
- **DO NOT** copy text from the sibling READMEs.
- **DO NOT** modify, regenerate or re-encode the media files. Do not add other images.
- **DO NOT** touch `PRDs/`, `.agents/`, `.claude/`, `CLAUDE.md`, `HACF-uninstall.sh`, HACF
  managed blocks or `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/**`.
- **DO NOT** add an email, `CITATION.cff` or version sections to the CHANGELOG.
- **DO NOT** let the guard call `git` or reach the network.
- **DO NOT** drop any slice-01 README requirement (nMap DOI, `Eta_Scripts`, licensing section,
  `uv` quickstart).
- **DO NOT** change product code under `src/eta_rxncat/` beyond an author string, if one exists.

## Proof contract

- [ ] `sha256sum media/logo.png media/banner.webp` matches the two hashes in Mini-requirement 1.
  `ls media/` lists exactly those two files.
- [ ] `head -6 README.md` shows the centered header with `./media/logo.png` width/height 200 and
  `<h1>Eta-RxnCat</h1>`. The banner `<img>` follows the header `</div>`. The README contains the
  four badges, a TOC whose every link matches a heading anchor (checked by a test or a short
  script), and the eight sections in order.
- [ ] `grep -c '10.1021/cs501828e' README.md` → ≥ 1; `grep -c 'Eta_Scripts' README.md` → ≥ 1.
- [ ] Every command in README "Usage" run as written → its documented exit code and output shape.
- [ ] `CHANGELOG.md` line 1 is `# Changelog`. It contains `## [Unreleased]`, `### Added`, and the
  Keep a Changelog and SemVer links. It has no `## [0.` heading.
- [ ] `sed -n 3p LICENSE` → `Copyright (c) 2026 Thomas J. L. Mustard Ph.D.`. The `pyproject.toml`
  authors name is the same form.
- [ ] `uv run pytest tests/unit/test_identity.py` → exit 0. The `tmp_path` cases show that the
  scanner flags `Thomas Mustard`, `Thomas J. Mustard`, `T. J. L. Mustard` and `Thomas J. L.
  Mustard, PhD`, accepts the canonical form and the surname-first citation, and skips an excluded
  path.
- [ ] The four gates → exit 0. The register rows from Mini-requirement 6 are present.

## Source material

- TJ's requirement (row `qitem-20261122123807-a377da3572ef57f8`) and banner note, quoted above.
- Sibling READMEs and the OIN-SMILES CHANGELOG (paths above, read-only).
- Mission `missions/release-0.1.0/SPEC.md` §5 trade-off log R34–R37; slice 01 SPEC (US-010).

## Intent visual

The README header, top to bottom: logo (200×200, centered), `Eta-RxnCat` h1, italic tagline, then
the banner at full width, the bold pitch, and the badge row. The intended look is
`~/AI/Hypergraph-Coding-Agent-Framework/README.md` lines 1–17 with the banner inserted after the
header.

## Status

- compiled

## Dependencies

- OPR.0.1.0.1 to OPR.0.1.0.6 (the README and CHANGELOG describe what those slices built)
