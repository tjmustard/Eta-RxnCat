# 03_mirror_image

The incoming set is the enantiomer of the template. A proper rotation cannot superimpose it, so RMSD must be 0.75 Å, not 0, and the moved incoming atoms must NOT equal the template. Product here is template (4) + whole moved incoming (4), deliberately with no deletions, to expose the coordinates. A mapper that silently reflects would wrongly report RMSD 0.

Expected alignment RMSD over the pairs: 0.750000 Å

Provenance: First principles input (template reflected through the xy plane); expected coordinates obtained by running the fit (independent quaternion fit and the original routine agree). Cross-check: an independent textbook quaternion (Horn 1987) fit and the original program's fitting routine agree to 2.2e-15 Å on every moved atom (original RMSD 0.750000 Å).
