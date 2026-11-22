---
id: OPR.0.1.0.10
slice: 10-logo-webp
mission: release-0.1.0
status: active
stage: wip
verified: "2026-11-22 against scaffold (hyper_scope slice create)"
created: "2026-11-22"
intent: "Replace slice 08's media with TJ's size-named WebP logo and banner sets (name = exact pixel size), embed only the next size up in the README, and add a stdlib test that enforces both rules."
depends_on: [OPR.0.1.0.8]
hacf_schema: 1
hacf_type: MiniPRD
hacf_status: executed
node_id: eta_rxncat_scaffold
parent: null
hacf_touches: ["media/**", README.md, tests/unit/test_identity.py, tests/unit/test_media.py, docs/prd/v0.1.0/DISCREPANCIES.md, spec/compiled/architecture.yml]
hacf_oracle: [["python3", "-c", "import hashlib,os,sys;E={'icons/icon-1024.webp': '01fa37d44142b91f80f2ebb32016ae11d97b65506553ec790f75e01dc50f0bca', 'icons/web/icon-128.webp': '5426246be4c8dfe7782106ad73342649fbea6713ec37584766d2c2cda1760d69', 'icons/web/icon-192.webp': '7a1a65b875c98f5cd610068975dcba21c3943be44e72aa43bf4c3ad11c98c69c', 'icons/web/icon-256.webp': 'd2d915459665c410088de30424605f695334f7c04896733f12e511ddb0428950', 'icons/web/icon-512.webp': '1accb65c99fdd1f9fb82ec5d2f988a03b8fd1e813876e5f4a9210165f09dd087', 'banner/banner-640x358.webp': '5c7398479c28f7614b57383a070aa00934bc73878a20019e1a778a98406e854e', 'banner/banner-1024x573.webp': '2abc89e6bd23e416409128b68916ee6ef036f9f82be072d6e4d15f7c10fc8387', 'banner/banner-1280x716.webp': '88ba6b9da4873029b188fd354516aa2cd1527aafe328218cefa75112b67887c5', 'banner/banner-1920x1073.webp': '9a2acc9b08b2633ca32520586c2a308e9a3b2899dd9956d94e2d1a3f6889e570', 'banner/banner-2576x1439.webp': '979e0f606ca321c108827dd946a84fe372cd760d744ad531a11a3cd0886e012c'};F={os.path.relpath(os.path.join(r,f),'media') for r,_,fs in os.walk('media') for f in fs};sys.exit(0 if F==set(E) and all(hashlib.sha256(open('media/'+k,'rb').read()).hexdigest()==v for k,v in E.items()) else 1)"], ["uv", "run", "ruff", "check", "."], ["uv", "run", "ruff", "format", "--check", "."], ["uv", "run", "mypy"], ["uv", "run", "pytest"], ["uv", "run", "pytest", "tests/unit/test_media.py", "tests/unit/test_identity.py"]]
lore_refs: []
hacf_legacy_source: null
hacf_legacy_order: null
---

# MiniPRD: Size-named WebP media set, next-size-up embedding, and a media test

## Intent

Replace slice 08's `media/logo.png` and `media/banner.webp` with TJ's set of WebP logo and banner
sizes. Every file is named by its exact pixel size. The README embeds only the next size up for
each displayed image, and a test enforces both rules.

Context the builder needs (self-contained). TJ's requests, verbatim:
- 15:10Z: "Can we make sure to convert the images to webp as well."
- 15:13Z: "Make a few different sizes like https://github.com/Eta-Partners/knowledge-domain-decks-skills"
- 15:22Z (via advisor-lead@kernel): "Make all image files names the exact size of the image inside
  128 for 128px. Make multiple sizes of the logo and banner. Only imbed the next size up for the
  documents."

This replaces replan 9's target (R51). The advisor encoded every file with `cwebp` q 90 from TJ's
sources (`logo.png`, and `banner-original.jpg`, TJ's final 13:05Z banner) and staged them in
`~/.hacf/eta-rxncat-hacf/incoming/media/` with `MANIFEST.sha256`. Resolve ran
`sha256sum -c MANIFEST.sha256` (10/10 OK) and checked that each file's WebP header size, its
Pillow-decoded size and its name all agree:

| Repo path | sha256 | WebP chunk | pixels | mode |
|---|---|---|---|---|
| `media/icons/icon-1024.webp` | `01fa37d44142b91f80f2ebb32016ae11d97b65506553ec790f75e01dc50f0bca` | VP8X | 1024×1024 | RGBA |
| `media/icons/web/icon-128.webp` | `5426246be4c8dfe7782106ad73342649fbea6713ec37584766d2c2cda1760d69` | VP8X | 128×128 | RGBA |
| `media/icons/web/icon-192.webp` | `7a1a65b875c98f5cd610068975dcba21c3943be44e72aa43bf4c3ad11c98c69c` | VP8X | 192×192 | RGBA |
| `media/icons/web/icon-256.webp` | `d2d915459665c410088de30424605f695334f7c04896733f12e511ddb0428950` | VP8X | 256×256 | RGBA |
| `media/icons/web/icon-512.webp` | `1accb65c99fdd1f9fb82ec5d2f988a03b8fd1e813876e5f4a9210165f09dd087` | VP8X | 512×512 | RGBA |
| `media/banner/banner-640x358.webp` | `5c7398479c28f7614b57383a070aa00934bc73878a20019e1a778a98406e854e` | VP8 | 640×358 | RGB |
| `media/banner/banner-1024x573.webp` | `2abc89e6bd23e416409128b68916ee6ef036f9f82be072d6e4d15f7c10fc8387` | VP8 | 1024×573 | RGB |
| `media/banner/banner-1280x716.webp` | `88ba6b9da4873029b188fd354516aa2cd1527aafe328218cefa75112b67887c5` | VP8 | 1280×716 | RGB |
| `media/banner/banner-1920x1073.webp` | `9a2acc9b08b2633ca32520586c2a308e9a3b2899dd9956d94e2d1a3f6889e570` | VP8 | 1920×1073 | RGB |
| `media/banner/banner-2576x1439.webp` | `979e0f606ca321c108827dd946a84fe372cd760d744ad531a11a3cd0886e012c` | VP8 | 2576×1439 | RGB (full-resolution master) |

About the banner master: `banner-2576x1439.webp` (`979e0f60…`, 229854 bytes) **replaces** slice 08's
`media/banner.webp` (`cc3fe67b…`, a Pillow q92 encode of the same banner).
- The advisor confirms both come from the same `banner-original.jpg`; this one is re-encoded with
  `cwebp`, so the whole set comes from one encoder.
- Resolve measured visual parity at 2576×1439: mean absolute difference under 1/255 per channel
  (max 18); downscaled luma PSNR 54.2 dB.

The staging folder also holds files that are **never** copied or committed: `logo.png`, `logo.webp`,
`banner-original.jpg`, `MANIFEST.sha256`, and every `old-*` file (including
`old-banner-unsized.webp`).

Slice 08 is audited and its SPEC is not edited. This slice replaces slice 08's committed media
and **updates slice 08's tests wherever they assert the README logo path, the README hero-banner
path or the media file set** (`tests/unit/test_identity.py::test_readme_header_and_banner` today).
Those files are in this slice's touches, and this slice's audit judges the change. From here on,
this slice's oracle supersedes slice 08's media check (R53). Node `eta_rxncat_scaffold` already
owns `media/**`, `README.md`, `docs/**` and the identity test. Add `tests/unit/test_media.py` to
the node's `files:` through `hyper_ledger.py ensure-node --files` (the full list) if it is not
covered.

## 1. The Confidence Mandate

**Score: 10/10.** Ten pinned files, two README lines, a deterministic next-size-up rule, and a
stdlib-only test with explicit failure cases.

## Mini-requirements

1. Media:
   - `git rm media/logo.png media/banner.webp`.
   - Copy the ten files byte for byte from the staging folder (same relative paths) into `media/`.
   - Verify all ten sha256s against the table (`sha256sum -c` of the staging manifest, with
     paths prefixed by `media/`).
   - `media/` then contains exactly these ten files at any depth: no PNG, no JPG, no unsized
     name.
2. Naming rule. Every file under `media/` must match exactly one pattern:
   - square: `icon-<N>.webp`, whose pixels are N×N;
   - non-square: `banner-<W>x<H>.webp`, whose pixels are W×H.
3. Embedding rule, "only embed the next size up":
   - an embedded image is a `<img src="./media/…">` tag (or a Markdown `![…](media/… or ./media/…)`)
     in any tracked `README.md`, `CHANGELOG.md` or `docs/**/*.md`, excluding the verbatim starter
     copy `docs/prd/v0.1.0/Eta-RxnCat-v0.1.0/**`;
   - external URLs (e.g. shields.io badges) are ignored;
   - the **declared display width** is the integer `width="<n>"` (px) attribute; `width="100%"`
     means the **README column width, a fixed constant of 1012 px** (GitHub's README content
     width);
   - a declared `height="<n>"` is also required to be ≤ the file's height;
   - an embedded image with no `width` attribute fails, and Markdown `![]()` has none, so local
     media must use `<img>`;
   - the **family** is the file's prefix (`icon` or `banner`), and the candidates are all
     `media/` files of that family;
   - the **required file** is the candidate with the smallest width that is ≥ the declared width
     (and with height ≥ any declared height); ties are impossible because names are unique;
   - the embedded file must be exactly the required file.
4. `README.md`. Only these two lines change:
   - line 2 → `    <img src="./media/icons/web/icon-256.webp" alt="Eta-RxnCat logo" width="200" height="200"/>`
     (displayed at 200, and 256 is the next size up over 128 and 192);
   - the hero line → `<p align="center"><img src="./media/banner/banner-1024x573.webp" alt="Eta-RxnCat banner" width="100%"/></p>`
     (100% = 1012 px, and 1024 is the next size up over 640).
5. New test file `tests/unit/test_media.py`. It is stdlib only (no Pillow), pure filesystem, and
   calls no git.
   - `webp_size(path) -> tuple[int, int]` reads the RIFF/WEBP header:
     - `VP8X`: canvas width−1 and height−1, 24-bit little-endian at bytes 24–26 and 27–29;
     - `VP8L`: signature `0x2F` at byte 20, then 14-bit width−1 and height−1 packed little-endian
       from byte 21;
     - `VP8 `: start code `9D 01 2A` at bytes 23–25, then 14-bit width and height at 26–27 and
       28–29;
     - anything else raises `ValueError`.
     
     Resolve checked this parsing against Pillow on all ten files.
   - `parse_media_name(name) -> tuple[family, w, h]` implements Mini-requirement 2 and raises on
     an unsized or foreign name.
   - `required_media(family, width, height, candidates) -> path` implements Mini-requirement 3.
   - `find_embeds(markdown_text) -> list[(src, width_px, height_px | None)]` implements the
     width rule.
   - Tests on the real repo:
     - the `media/` file set equals the ten paths;
     - every file's `webp_size` equals its parsed name;
     - every embed in the scanned docs uses its required file;
     - the README embeds exactly `icon-256` and `banner-1024x573`.
   - Synthetic `tmp_path` tests, using hand-built minimal WebP headers for each chunk type. Each
     must FAIL the check:
     - (a) a mismatched name (`icon-256.webp` whose header says 255×255);
     - (b) an oversized choice (`icon-512` embedded at `width="200"`);
     - (c) an undersized choice (`icon-192` at `width="200"`);
     - (d) an unsized name (`banner.webp`);
     - (e) a local embed with no width;
     - (f) `width="100%"` resolving to `banner-1280x716` instead of `banner-1024x573`.
     
     One passing case per chunk type.
6. `tests/unit/test_identity.py::test_readme_header_and_banner`: its two asserted lines change to
   the Mini-requirement 4 lines. Any other slice-08 assertion of `media/logo.png`,
   `media/banner.webp` or the media set is updated the same way.
7. `docs/prd/v0.1.0/DISCREPANCIES.md` gains these rows, each with status `open`; D-400 and D-401
   stay as history:
   - a `changed` row: `media/logo.png` → the icon set, README logo `icons/web/icon-256.webp`;
   - a `changed` row: `media/banner.webp` (`cc3fe67b…`) → `banner/banner-2576x1439.webp`
     (`979e0f60…`, same image re-encoded), plus the four smaller sizes, README hero
     `banner-1024x573`;
   - an `added` row for `tests/unit/test_media.py`.
   
   Cite R53 and TJ 15:10Z / 15:13Z / 15:22Z.

## 3. Implementation Plan (Task List)

- [x] Task 1: media swap and sha verification (Mini-requirement 1).
- [x] Task 2: the two README lines (Mini-requirement 4).
- [x] Task 3: `tests/unit/test_media.py` (Mini-requirement 5). First see the synthetic failure
  cases fail against a deliberately wrong fixture, then pass.
- [x] Task 4: update the slice-08 assertions (Mini-requirement 6).
- [x] Task 5: register rows, then the four gates, then `hypergraph_updater.py`.

## 4. The Negative Space (Constraints)

- **DO NOT** edit slice 08's SPEC, proof or oracle.
- **DO NOT** re-encode, resize or generate any image. Copy the staged files byte for byte.
- **DO NOT** commit `logo.png`, `logo.webp`, `banner-original.jpg`, `MANIFEST.sha256` or any
  `old-*` file. Leave no PNG, JPG or unsized name under `media/`.
- **DO NOT** change any other README line, or embed local media without a `width`.
- **DO NOT** use Pillow or any non-stdlib library in `tests/unit/test_media.py`.
- **DO NOT** touch `.agents/` (its template's commented `logo.png` is HACF-managed) or `PRDs/`.

## Proof contract

- [ ] `find media -type f | sort` lists exactly the ten paths. Each sha256 matches the table
  (`cd media && sha256sum -c <staged MANIFEST>` → 10 OK).
- [ ] `git ls-files media` lists exactly the ten paths. `git ls-files media | grep -vE '/(icon-[0-9]+|banner-[0-9]+x[0-9]+)\.webp$'`
  is empty.
- [ ] `git grep -nE "media/(logo\.(png|webp)|banner\.webp)" -- README.md CHANGELOG.md src tests docs ':!docs/prd/v0.1.0/DISCREPANCIES.md' ':!docs/prd/v0.1.0/Eta-RxnCat-v0.1.0'`
  finds nothing.
- [ ] `sed -n 2p README.md` and the hero line equal the exact lines in Mini-requirement 4.
- [ ] `uv run pytest tests/unit/test_media.py tests/unit/test_identity.py` → exit 0, with every
  synthetic case (a)–(f) asserted to fail the check and the passing cases to pass.
- [ ] The four gates (`uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`,
  `uv run pytest`) → exit 0.

## Source material

- TJ 15:10Z, 15:13Z, 15:22Z (quoted above); the lead's replan rows 8, 9 and 11; the advisor's
  banner-master note (15:22Z).
- `missions/release-0.1.0/slices/08-repo-identity/SPEC.md` (context only).
- Mission `missions/release-0.1.0/SPEC.md` trade-off log R34, R36, R40, R50, R51, R53.

## Intent visual

The README header layout is unchanged. The logo is `icons/web/icon-256.webp` displayed at
200×200, and the hero is `banner/banner-1024x573.webp` at full column width.

## Status

- compiled

## Dependencies

- OPR.0.1.0.8 (repo identity: README header, media, identity test)
