# 01_rigid_recovery

The fit must undo the motion exactly: the extra O atom must land at (1,1,1) and RMSD must be 0. Product = 4 template atoms then the O.

Expected alignment RMSD over the pairs: 0.000000 Å

Provenance: First principles: the incoming structure is the template rotated 0.7 rad about axis (1,2,3) and translated by (5,-2,1), plus one extra atom at the image of (1,1,1). Cross-check: an independent textbook quaternion (Horn 1987) fit and the original program's fitting routine agree to 1.4e-15 Å on every moved atom (original RMSD 0.000000 Å).
