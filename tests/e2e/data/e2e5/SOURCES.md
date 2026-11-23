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
