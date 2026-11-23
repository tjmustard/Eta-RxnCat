# 07_delete_lists_and_order

Provenance: first principles (hand-built and hand-computed). Confirmed by running the original V2 tool, which gives the same six atoms and coordinates in its incoming-first order.

Incoming is the template's paired atoms shifted by +10 Å in x, so the fit is a pure translation of −10 Å in x (rotation = identity, RMSD 0). The three pairs (template 1,4,5 ← incoming 1,2,3) are not collinear.

Delete lists, written in the original's range syntax:
- template "2-3 5 4-3 5": "2-3" is the inclusive range {2,3}; "5" appears twice (duplicate, harmless to the selection); "4-3" is a reversed range and contributes nothing. Expanded set {2,3,5}.
- incoming "1-2 1": {1,2} with a duplicate. Expanded set {1,2}.

Product (template-first order):
- kept template atoms 1, 4, 6 → product 1, 2, 3 (index = n − number of deleted template indices below n: 1−0, 4−2, 6−3).
- kept incoming atoms 3, 4, 5 → product 4, 5, 6 (index = 3 kept template atoms + m − number of deleted incoming indices below m: 3+3−2, 3+4−2, 3+5−2), at their moved coordinates.

Incoming atom 3 is a *paired* atom that was not deleted, so it appears in the product: the original appends every non-deleted incoming atom, not only unpaired ones (spec §5.1, §10 Q1).

Original-defect note: the batch tool would write an atom-count header of 6 + 5 − 4 − 3 = 4 for this request (it subtracts expanded list lengths, duplicates included: the template list expands to 2,3,5,5 and the incoming list to 1,2,1), while 6 atom lines follow. The correct count is 6.

Expected alignment RMSD over the pairs: 0.000000 Å
