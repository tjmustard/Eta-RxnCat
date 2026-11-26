# Sources: TJ's 5-tier E2E structures for Tiers 1 and 2 (v0.3.0)

TJ, Q-E4 (verbatim): "Q4. A but the files attached can be used as reference." The four XYZ below
are TJ's, taken byte-identical from the `XYZ_FILES` literal of his bundle builder (read with
`ast.parse` + `ast.literal_eval`; the builder was never executed). Neither the builder nor the SI
PDFs are committed.

- Builder: `~/.hacf/eta-rxncat-hacf/incoming/e2e-5tier-20261123/Eta-RxnCat_5-Tier_E2E_Bundle_Zip_Builder.py`,
  sha256 `26e923529370687f78dffccbfa6f613f1e7391d50c425432c5f600ff86acc8e2`, equal to its line in
  `MANIFEST.sha256` of the same directory (checked 2026-11-23).
- Citation for every file: Liu, Paton, Kim, Liang, Houk, *J. Am. Chem. Soc.* 2013, 135, 15642,
  DOI 10.1021/ja408437u, Supporting Information. Level of theory (from each header):
  M06-2X/6-31G(d). Transcriber: TJ.

| File | SI page | Header energies (Eh) | sha256 |
|---|---|---|---|
| `xyz/2_dimethoxybutadiene.xyz` | S6 | E −384.866192, G −384.744596 | `12afa0690b7b3eac442032b35ac98b92534be93afd14bd6b09353f25fb3c8111` |
| `xyz/1_cyclopentadiene.xyz` | S6 | E −194.004692, G −193.937241 | `db8390fcc9fc9212d3fd7702f40d40a86eb673bc05fe8b4589b10785a83bf812` |
| `xyz/5_cyclopropene.xyz` | S7 | E −116.562552, G −116.529371 | `e61f12a6a2a1ea3f095f2bcd55153a0469afc01518a727371eb0a5ef7958a8b2` |
| `xyz/P1a_n.xyz` | S18 | E −310.649183, G −310.518060 | `c7b9792c062bdff47125a237620b1fc4e4b81d3b0c241daf7008de00ab0e5d7a` |
| `xyz/TS1a_n.xyz` | S8 | E −310.559154, G −310.435319 | `c43753744532f36b0a3ac77b6797e7442a9dd0ee246c84edf76a34ea5810f267` |
| `xyz/6_cyclobutene.xyz` | S7 | E −155.890853, G −155.828875 | `8b25312f3c3b4948c4d3d4de6cdd2396516147dc5fc52ed2d94f7a259ab4e990` |
| `xyz/TS1b_n.xyz` | S8 | E −349.874922, G −349.721825 | `677d570d68f4d51cdf2efb29474cb26751e617b811350f77bf532d4d6785a457` |

The last three rows (`TS1a_n`, `6_cyclobutene`, `TS1b_n`) are Fixture M1 (v0.4.0, Tier 3 of the
5-tier spec), extracted the same way from the same builder (`ast.parse` + `ast.literal_eval` of
`XYZ_FILES`; never executed) on 2026-11-23; their SI pages and energies are from each file's own
header line (TS1a_n's header does not state the level of theory).

Derived SMILES (H10; RDKit 2026.09.2 `DetermineBonds(charge=0)` + `AssignStereochemistryFrom3D`),
for TJ's confirmation at Phase 3: T1 `C=C(/C=C/OC)OC`; Cp `C1=CCC=C1`; cyclopropene `C1=CC1`;
P1a_n `C1=C[C@H]2C[C@@H]1[C@H]1C[C@H]12` (meso, endo).

## Tier 3 (v0.5.0): transcriptions for the TS fixtures

TJ A3, verbatim: "Q3. A". The team transcribes TS3a, TS4a, cyclobutenone and TS N4 from the SIs
TJ attached, and TJ confirms them at Phase 3. The procedure is `pdftotext` per (half) page plus a
fixed atom regex, with coordinate strings copied verbatim (mission HF-1). It was run first by
spec-resolve and then independently in slice 07 by the execute seat; the two outputs are byte-equal
and equal to the mission's HF-1 sha256s. Tetrazines 3 and 4 are TJ's, taken byte-identical from the
`XYZ_FILES` literal of his builder (read with `ast.parse` + `ast.literal_eval`; never executed).
Neither the SI PDFs nor any extracted SI text are committed.

- Liu, Paton, Kim, Liang, Houk, *J. Am. Chem. Soc.* 2013, 135, 15642, DOI 10.1021/ja408437u,
  Supporting Information (`ja408437u_SI.pdf`, sha256
  `98f37dc41f252f4e031e750d9343c3c478d4e5651940c3d0ed54e587b476f6af`). M06-2X/6-31G(d).
- Paton et al., *Angew. Chem. Int. Ed.* 2011, 50, 10366, DOI 10.1002/anie.201103998, Supporting
  Information (`anie_201103998_SI_Paton2011.pdf`, sha256
  `a38b2362232940c05f20ae921cee6a04aef58d98811c066e1de003676f043af6`). M06-2X/6-31G(d).
  **E(thermal) is the thermally corrected energy, not the electronic energy**; Paton's SI prints no
  electronic E, so no Paton file is checked against an electronic energy.

| File | Source | SI page | Energies as printed (Eh) | sha256 | Transcriber |
|---|---|---|---|---|---|
| `xyz/TS3a.xyz` | Liu | S15 (17 atoms, left column, + 4, right) | E −491.366826, H −491.187576, G −491.232873 | `6bf308b6846732718499d2370f355116a849a232f476c27a026dafb5ab1ea1b4` | team (spec-resolve; slice 07 re-transcription) |
| `xyz/TS4a.xyz` | Liu | S17 | E −1086.627595, H −1086.490471, G −1086.545437, Gsol −1086.883262 | `b00f6a874efd2b30112e34d2cb16892923f73b756e7bdbca4a2f6583b4bf008c` | team (spec-resolve; slice 07 re-transcription) |
| `xyz/cyclobutenone.xyz` | Paton | S3 | E(thermal) −229.814586, H −229.813642, G −229.845861 | `c489e5124f42895bb0408f127aa10d51db70ccfbd72f4cf5c929c10052f4f30c` | team (spec-resolve; slice 07 re-transcription) |
| `xyz/TS_N4.xyz` | Paton | S6 | E(thermal) −423.703397, H −423.702453, G −423.744120 | `cf7e45014bdab5971b2c993da3f2d5125ce744a8def5bda64998e047dc3dc46f` | team (spec-resolve; slice 07 re-transcription) |
| `xyz/3_dimethyltetrazine.xyz` | Liu | S6 | E −374.809570, G −374.733585 | `e42ed53adaa7bc3a9fe542d88cafb632d4351c3e419e9b2b3b3b961744a7662d` | TJ (builder `XYZ_FILES`; slice 07 extraction) |
| `xyz/4_bis_cf3_tetrazine.xyz` | Liu | S6 | E −970.056992, G −970.031351 | `174c23d2c794196f7d1fa5367529fe623e1529007bab76cb32b9139816e92f74` | TJ (builder `XYZ_FILES`; slice 07 extraction) |

The Paton energies of cyclopentadiene, used for the N4 reference below, are as printed on Paton SI
S2: E(thermal) −193.906541, H −193.905597, G −193.937243. Paton's Cp G equals Liu's −193.937241
to 2e-6 Eh, so the two SIs share a level of theory and a standard state.

## References (mission HF-9, R8)

Each ΔG‡ below is header G arithmetic: G(TS) − G(diene) − G(dienophile), × 627.5094740631
kcal/mol per Eh. **Standard state:** both SIs are Gaussian at 1 atm, and Paton's SI states free
energies at 298 K with no concentration correction. The 1 M value is 1 atm − RT ln(cRT/p) with
Δn = −1, which is 1 atm − 1.8943 kcal/mol at 298.15 K. The fixture windows are the 1 M value ± 7
kcal/mol (TJ A4), except TS1b_n, where TJ set [20, 34].

| TS | Reactants (G used, Eh) | G(TS) (Eh) | ΔG‡ 1 atm (kcal/mol) | ΔG‡ 1 M (kcal/mol) |
|---|---|---|---|---|
| TS1a_n | Cp −193.937241 (Liu), cyclopropene −116.529371 | −310.435319 | 19.637 | 17.742 |
| TS1b_n | Cp −193.937241 (Liu), cyclobutene −155.828875 | −349.721825 | 27.793 | 25.899 |
| TS3a | tetrazine 3 −374.733585, cyclopropene −116.529371 | −491.232873 | 18.877 | 16.983 |
| TS4a | tetrazine 4 −970.031351, cyclopropene −116.529371 | −1086.545437 | 9.591 | 7.697 |
| N4 | Cp −193.937243 (Paton), cyclobutenone −229.845861 | −423.744120 | 24.463 | 22.569 |

## Tier 4 (v0.6.0): the exo structures

TJ Q-E4, verbatim: "Q4. A but the files attached can be used as reference." The team transcribes
TS1b_x and P1b_x from Liu's SI and TJ confirms them at Phase 3. TS1a_x is TJ's, taken byte-identical
from the `XYZ_FILES` literal of his builder (`ast.parse` + `ast.literal_eval`; never executed; the
builder's sha256 is the one above, equal to its line in `MANIFEST.sha256`).

Procedure for the two transcribed files (mission HF-1), run in a scratch directory by spec-resolve
and again, independently, by the execute seat in slice 08; the outputs are byte-equal and equal to
the mission's sha256s. `pdftotext -f <p> -l <p> -x <0|300> -y 0 -W <300|312> -H 792 -layout
ja408437u_SI.pdf liu_p<p>_<L|R>.txt` (left column `-x 0 -W 300`, right column `-x 300 -W 312`) for
p = 9 (both columns), 10 (left) and 20 (both). TS1b_x is the one atom line after the `TS1b_x` label in
`liu_p9_R.txt` plus the first 20 atom lines of `liu_p10_L.txt`; P1b_x is the 21 atom lines after the
`P1b_x` label in `liu_p20_R.txt`. An atom line is matched whole by
`([A-Z][a-z]?)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)` and its coordinate strings are copied
verbatim; the file is `"<N>\n<header>\n"` and one `S x y z\n` per atom. Neither the SI PDF nor any
extracted text is committed. The SI is Liu, Paton, Kim, Liang, Houk, *J. Am. Chem. Soc.* 2013, 135,
15642 (`ja408437u_SI.pdf`, sha256 `98f37dc41f252f4e031e750d9343c3c478d4e5651940c3d0ed54e587b476f6af`),
M06-2X/6-31G(d).

| File | Source | SI page | Energies as printed (Eh) | sha256 | Transcriber |
|---|---|---|---|---|---|
| `xyz/TS1a_x.xyz` | Liu | S9 | E −310.551522, G −310.428509 | `ec319a528d3efd0d7c14fb1d018d31d57eae85e794df59761665ed4d0f684d60` | TJ (builder `XYZ_FILES`; slice 08 extraction) |
| `xyz/TS1b_x.xyz` | Liu | S9 (right, 1 atom) + S10 (left, 20 atoms) | E −349.872275, H −349.679329, G −349.718879 | `2a0b8362cdd36464c5f3f7a196927005c1cc933f3fdc6a693ae0d56ff365fd82` | team (spec-resolve; slice 08 re-transcription) |
| `xyz/P1b_x.xyz` | Liu | S20 (right) | E −349.957548, G −349.797634 | `ca8706431f6e8b57662a3f65196a9ca3cba3288a4eda68308f7bc3c9699b5eec` | team (spec-resolve; slice 08 re-transcription) |

TS1a_x's header does not state the level of theory; TS1b_x and P1b_x state M06-2X/6-31G(d).

Derived SMILES of P1b_x (RDKit 2026.09.2 `DetermineBonds(charge=0)` + `AssignStereochemistryFrom3D`),
for TJ's confirmation at Phase 3: `C1=C[C@H]2C[C@@H]1[C@@H]1CC[C@@H]12` (the exo adduct of Cp and
cyclobutene; P1a_n above is the endo adduct of Cp and cyclopropene).

## Tier 4 references (mission HF-2, M3)

Each ΔΔG‡ is header G arithmetic, G(exo TS) − G(endo TS), × 627.5094740631 kcal/mol per Eh. TJ's
+4.3 and +1.8 are the window centres; Liu's values are recorded beside them.

| Pair | G(exo) (Eh) | G(endo) (Eh) | ΔΔG‡ (kcal/mol) | TJ |
|---|---|---|---|---|
| TS1a_x − TS1a_n (unmapped) | −310.428509 | −310.435319 | 4.273 | +4.3 |
| TS1b_x − TS1b_n (mapped) | −349.718879 | −349.721825 | 1.849 | +1.8 |

## Tier 4 flexible-ensemble fragments (v0.6.0, slice 14; mission R29, HF-14)

TJ's amended Q-RES1 B (verbatim): "Can we r-group enumerate a new TS from with a alkyl chain". The
three files below are generated, not transcribed: 3-R-cyclopropenes (SMILES `CCC1C=C1`,
`CCCC1C=C1`, `CCCCC1C=C1`) built with RDKit 2026.09.2 `Chem.AddHs`, then ETKDGv3 with
`randomSeed=42`, then `MMFFOptimizeMolecule`, then the chain set all-anti with
`rdMolTransforms.SetDihedralDeg`: the ring-H - ring C(sp3) - C-alpha - C-beta dihedral to 180°, then
every C-C-C-C dihedral outward to 180° (the plain ETKDG conformer of n-propyl folds the chain onto
the ring and the graft refuses it). Written once with 6 decimals by
`tests/e2e/t4_flexible.py::write_fragment_xyz`. They graft onto `xyz/TS1a_n.xyz` (above) through
`t4_flexible_alkyl.yaml`; the sp2 pair order of each is the lower alignment fit.

| File | SMILES | Generated | sha256 |
|---|---|---|---|
| `xyz/r_ethyl_cyclopropene.xyz` | `CCC1C=C1` | RDKit 2026.09.2, recipe above | `ea69e03013d57e3d847dffebad86840f9225669405526100cb32233c59ceb4d0` |
| `xyz/r_npropyl_cyclopropene.xyz` | `CCCC1C=C1` | RDKit 2026.09.2, recipe above | `e30b55b51a993b294d168e8230d9d5bb2026dbe02be883be98c5be474dfcee56` |
| `xyz/r_nbutyl_cyclopropene.xyz` | `CCCCC1C=C1` | RDKit 2026.09.2, recipe above | `d9d00a49a4d892ce633da4f61ea86b9f205b4d6ce98ca844c92f4460c2a7af50` |

## v0.7.0 E2E inputs (slice 10)

`v070_enumeration.yaml` and `v070_fallback.yaml` (loaded by `tests/e2e/v070.py`) use only existing
files; no geometry is new. Their provenance is in the sections above.

| File | Role | Provenance | sha256 |
|---|---|---|---|
| `xyz/1_cyclopentadiene.xyz` | reactant `cyclopentadiene` | Liu SI (TJ builder), above | `db8390fcc9fc9212d3fd7702f40d40a86eb673bc05fe8b4589b10785a83bf812` |
| `xyz/5_cyclopropene.xyz` | reactant `cyclopropene` | Liu SI (TJ builder), above | `e61f12a6a2a1ea3f095f2bcd55153a0469afc01518a727371eb0a5ef7958a8b2` |
| `xyz/TS1a_n.xyz` | TS `TS1a_n` (endo) | Liu SI (TJ builder), above | `c43753744532f36b0a3ac77b6797e7442a9dd0ee246c84edf76a34ea5810f267` |
| `xyz/TS1a_x.xyz` | TS `TS1a_x` (exo) | Liu SI (TJ builder), above | `ec319a528d3efd0d7c14fb1d018d31d57eae85e794df59761665ed4d0f684d60` |
| `xyz/r_ethyl_cyclopropene.xyz` | library `ethyl` | generated, slice-14 recipe above | `ea69e03013d57e3d847dffebad86840f9225669405526100cb32233c59ceb4d0` |
| `xyz/r_npropyl_cyclopropene.xyz` | library `npropyl` | generated, slice-14 recipe above | `e30b55b51a993b294d168e8230d9d5bb2026dbe02be883be98c5be474dfcee56` |

**Reactant map on `5_cyclopropene.xyz`** (site `c7`, measured in slice 10). The reactant has no
diene, so the anti-H rule cannot apply: the map keeps the CH2 H that the fragment's `ring_h` pairs
with (atom 3; alignment [0, 1, 2, 3]) and deletes the other (atom 4), which R replaces. The two H
are mirror images (keeping atom 4 gives the same fits with the sp2 orders swapped). Fits (Angstrom,
superposition RMSD, 0 close contacts): ethyl [2, 3, 4, 10] 0.0525, other order 0.4888; n-propyl
[3, 5, 4, 13] 0.0496, other order 0.4859. Both chosen fits are within the plan's 0.15.
