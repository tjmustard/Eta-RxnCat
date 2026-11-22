---
id: OPR.0.1.0.10
slice: 10-logo-webp
mission: release-0.1.0
status: active
stage: wip
verified: "2026-11-22 against scaffold (hyper_scope slice create)"
created: "2026-11-22"
intent: "Replace media/logo.png with TJ's WebP icon-size set (icons/icon-1024, icons/web/icon-128..512) and a README-size banner-1280, and point the README header at them, so media/ holds only WebP files."
depends_on: [OPR.0.1.0.8]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: compiled
node_id: eta_rxncat_scaffold
parent: null
hacf_touches: ["media/**", README.md, tests/unit/test_identity.py, docs/prd/v0.1.0/DISCREPANCIES.md, spec/compiled/architecture.yml]
hacf_oracle: [["python3", "-c", "import hashlib,os,sys;E={'icons/icon-1024.webp': '01fa37d44142b91f80f2ebb32016ae11d97b65506553ec790f75e01dc50f0bca', 'icons/web/icon-128.webp': '5426246be4c8dfe7782106ad73342649fbea6713ec37584766d2c2cda1760d69', 'icons/web/icon-192.webp': '7a1a65b875c98f5cd610068975dcba21c3943be44e72aa43bf4c3ad11c98c69c', 'icons/web/icon-256.webp': 'd2d915459665c410088de30424605f695334f7c04896733f12e511ddb0428950', 'icons/web/icon-512.webp': '1accb65c99fdd1f9fb82ec5d2f988a03b8fd1e813876e5f4a9210165f09dd087', 'banner-1280.webp': '88ba6b9da4873029b188fd354516aa2cd1527aafe328218cefa75112b67887c5', 'banner.webp': 'cc3fe67b17ea6e75358f9461623af2a814b75d2d724cb8842b11d751c8e9290f'};F={os.path.relpath(os.path.join(r,f),'media') for r,_,fs in os.walk('media') for f in fs};sys.exit(0 if F==set(E) and all(hashlib.sha256(open('media/'+k,'rb').read()).hexdigest()==v for k,v in E.items()) else 1)"], ["uv", "run", "ruff", "check", "."], ["uv", "run", "ruff", "format", "--check", "."], ["uv", "run", "mypy"], ["uv", "run", "pytest"], ["uv", "run", "pytest", "tests/unit/test_identity.py"]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: WebP media set: icon sizes and a README-size banner

## Intent

Replace `media/logo.png` with TJ's set of WebP icon sizes, add a README-size banner, and point the
README header at them, so `media/` holds only WebP files.

Context the builder needs (self-contained). TJ, 15:10Z: "Can we make sure to convert the images to
webp as well." TJ, 15:13Z (via advisor-lead@kernel): "Make a few different sizes like
https://github.com/Eta-Partners/knowledge-domain-decks-skills". This set supersedes the single
`logo.webp` (`a030acba…`), which is no longer used.

The advisor encoded the files from `logo.png` (`cwebp` q 90, `alpha_q` 100, transparency kept) and
staged them in `~/.hacf/eta-rxncat-hacf/incoming/media/`. Resolve verified each one on disk:

| Staged path (= repo path under `media/`) | sha256 | bytes | pixels | alpha |
|---|---|---|---|---|
| `icons/icon-1024.webp` | `01fa37d44142b91f80f2ebb32016ae11d97b65506553ec790f75e01dc50f0bca` | 63524 | 1024×1024 | yes |
| `icons/web/icon-128.webp` | `5426246be4c8dfe7782106ad73342649fbea6713ec37584766d2c2cda1760d69` | 3784 | 128×128 | yes |
| `icons/web/icon-192.webp` | `7a1a65b875c98f5cd610068975dcba21c3943be44e72aa43bf4c3ad11c98c69c` | 6656 | 192×192 | yes |
| `icons/web/icon-256.webp` | `d2d915459665c410088de30424605f695334f7c04896733f12e511ddb0428950` | 9756 | 256×256 | yes |
| `icons/web/icon-512.webp` | `1accb65c99fdd1f9fb82ec5d2f988a03b8fd1e813876e5f4a9210165f09dd087` | 25668 | 512×512 | yes |
| `banner-1280.webp` | `88ba6b9da4873029b188fd354516aa2cd1527aafe328218cefa75112b67887c5` | 80746 | 1280×716 | no (source has none) |
| `banner.webp` (already in the repo, unchanged full-resolution master) | `cc3fe67b17ea6e75358f9461623af2a814b75d2d724cb8842b11d751c8e9290f` | 279188 | 2576×1439 | no |

The icons are lossy colour with exact alpha, so there is no pixel-identity claim against
`logo.png`. The staging folder also holds files that are **never** copied or committed:
`logo.png`, the root `logo.webp`, `banner-original.jpg`, and every `old-*` file.

Slice 08 (its SPEC is not edited here) built the README header, `media/` and
`tests/unit/test_identity.py`, which asserts the README's logo and banner lines. **This slice
updates slice 08's tests wherever they, as they stand after slice 08's audit, assert:**
- the README logo path;
- the README hero-banner path;
- the set of files in `media/`.

Those test files are in this slice's touches, and this slice's audit judges the change. Slice 08's
own oracle pins `media/logo.png` at its own audit commit; from here on, this slice's oracle
supersedes that media check (R50, R51). Node `eta_rxncat_scaffold` already owns `media/**`,
`README.md`, `docs/**` and `tests/unit/test_identity.py`.

## 1. The Confidence Mandate

**Score: 10/10.** Seven pinned files, two README lines and the matching test assertions, all
checked deterministically.

## Mini-requirements

1. Media:
   - `git rm media/logo.png`.
   - Copy the six new files byte for byte from the staging folder to the same relative paths
     under `media/`. Keep `media/banner.webp` unchanged.
   - Verify all seven sha256s against the table.
   - Afterwards `media/` contains exactly those seven files, and nothing else at any depth.
2. `README.md`. Only these two lines change:
   - line 2 becomes exactly
     `    <img src="./media/icons/web/icon-512.webp" alt="Eta-RxnCat logo" width="200" height="200"/>`;
   - the hero line becomes exactly
     `<p align="center"><img src="./media/banner-1280.webp" alt="Eta-RxnCat banner" width="100%"/></p>`.
3. Tests:
   - In `tests/unit/test_identity.py`, change every assertion of the old logo path
     (`./media/logo.png`) or old hero path (`./media/banner.webp` as the README image) to the
     new paths, plus any media-set assertion.
   - Add `test_media_is_webp_set`. It is pure filesystem and calls no git. It asserts that:
     - the recursive file set of `media/` equals the seven paths;
     - every file starts with `RIFF` and has `WEBP` at byte 8;
     - each `icon-<N>.webp` decodes to N×N RGBA with a non-constant alpha channel (Pillow is in
       the dev env);
     - `banner-1280.webp` is 1280 pixels wide.
4. `docs/prd/v0.1.0/DISCREPANCIES.md` gains these rows, each with status `open`:
   - a `changed` row: `media/logo.png` → the icon set, with the README logo set to
     `icons/web/icon-512.webp` (TJ 15:10Z / 15:13Z, R51);
   - an `added` row for `media/banner-1280.webp` as the README hero; the master `banner.webp` is
     kept.
   
   D-400 and D-401 stay as history.

## 3. Implementation Plan (Task List)

- [ ] Task 1: media swap and sha verification (Mini-requirement 1).
- [ ] Task 2: the two README lines (Mini-requirement 2).
- [ ] Task 3: test updates and `test_media_is_webp_set` (Mini-requirement 3).
- [ ] Task 4: register rows. Run the four gates, then `hypergraph_updater.py`.

## 4. The Negative Space (Constraints)

- **DO NOT** edit slice 08's SPEC, proof or oracle.
- **DO NOT** re-encode, resize or generate any image. Copy the staged files byte for byte.
- **DO NOT** commit `logo.png`, the root staged `logo.webp`, `banner-original.jpg` or any `old-*`
  file. No PNG or JPG may exist anywhere under `media/`.
- **DO NOT** change any other README line.
- **DO NOT** touch `.agents/` (its template's commented `logo.png` is HACF-managed) or `PRDs/`.

## Proof contract

- [ ] `find media -type f | sort` lists exactly the seven paths, and each one's sha256 and byte
  count match the table.
- [ ] `git ls-files media` lists exactly those seven paths. `git ls-files media | grep -E '\.(png|jpe?g)$'`
  is empty.
- [ ] `git grep -nE "media/logo\.(png|webp)" -- README.md CHANGELOG.md src tests docs ':!docs/prd/v0.1.0/DISCREPANCIES.md' ':!docs/prd/v0.1.0/Eta-RxnCat-v0.1.0'`
  finds nothing.
- [ ] `sed -n 2p README.md` and the hero line equal the exact lines in Mini-requirement 2.
- [ ] `uv run pytest tests/unit/test_identity.py` → exit 0, including `test_media_is_webp_set`.
- [ ] The four gates (`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`,
  `uv run pytest`) → exit 0.

## Source material

- TJ 15:10Z and 15:13Z (quoted above); the lead's replan rows for replan 8 and 9.
- `missions/release-0.1.0/slices/08-repo-identity/SPEC.md` (context only).
- Mission `missions/release-0.1.0/SPEC.md` trade-off log R34, R36, R40, R50, R51.

## Intent visual

The README header layout is unchanged. The logo now comes from `icons/web/icon-512.webp`, shown at
200×200, and the hero image from `banner-1280.webp` at full width.

## Status

- compiled

## Dependencies

- OPR.0.1.0.8 (repo identity: README header, media, identity test)
