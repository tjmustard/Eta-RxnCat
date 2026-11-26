# Slice 18 resume notes (build-execute, stopped on usage limit)
Start cd2a91e. Row qitem-20261126211155-c9f544cc688d1c35 (in-progress).

## Done
- executing event; codegraph `index: ok`
- code commit fb32253 (harness retarget, review_g15.py, record writer, tests; 59 helper/record tests pass; ruff, format, mypy exit 0)
- uv sync --locked 0; `v070-slice18/run.sh bundle 3600` exit 0 at fb32253: 7 sub-bundles, 0 engine calls, 11977758 bytes,
  root manifest sha256 5ad4aa3b9a8dc8cfbb42ea07c73b5311c27826ef276b52d3130de1a4378332ec, 44 files; G15 pass (proof/bundle.log)
- candidate-only commit 1abbe17 (44 files; git index blob ids equal hash-object of scratch; candstat.txt)
- M12 on scratch tree: Chrome 158 and Playwright Firefox 159, 759/0 each (68 TS animated, 304 plays, 116 disposition
  options, 0 identity banners, 4 known-answer pages); driver and logs in proof/m12. Screenshots NOT yet viewed.
- previous record: v070-replan7-runs/proof/acceptance-slice13.json (git show cd2a91e:docs/prd/v0.7.0/ACCEPTANCE_RESULT.json,
  sha256 11d2408ac3252a6c118c6011ca0aa155f48848c9dc02260650919cb411894bcb)

## Left
1. View known-*.png. Remove throwaway $TMPDIR/slice18/{pwvenv,pw-browsers,dry-review} (plain rm, literal paths).
2. Full check at HEAD (host check first): uv sync --locked; ruff check .; format --check with the two excludes; mypy;
   uv run pytest > v070-slice18/proof/full-pytest.log (ETA_RXNCAT_XTB set); the two oracle test files; all under timeout 3600.
3. uv run --no-sync python tests/e2e/acceptance_record_v070.py $E missions/release-0.7.0/slices/17-rerun-units/proof/17-execute.md
   $D/proof/full-pytest.log <exit> docs/prd/v0.7.0/ACCEPTANCE_RESULT.json
4. proof/18-execute.md incl. Phase 3 row draft (values from records; graft_time "Rank used" shows renumbered 1 note;
   UMA gates reported only); tick SPEC task and proof boxes (none ticked yet).
5. ensure-node --from-spec; record+progress commit; codegraph index; updater ONCE --from-diff cd2a91e --apply
   --slice OPR.0.7.0.18; progress --event executed; field notes; handoff to orch-lead.

## Disclose to audit
- One command that included `ls tests/candidate_outputs/...` (a listing) was permission-denied; nothing ran; rerun without it.
- Dry build into $TMPDIR before the official run (dry.py), after its own host check; same manifest sha; no candidate write.
- M12 host check refused once-then-twice on another project's transient python (oin-v1-w7-a fuzz.py); waited until free.
- 0 TS identity failures in this bundle, so no identity banner appears on the real page (say so to TJ).
- Source.slice_name renamed to group; root index column "Source". Floor 4 GiB per lead ruling in the brief.
