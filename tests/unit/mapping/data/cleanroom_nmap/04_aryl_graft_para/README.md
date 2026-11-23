# 04_aryl_graft_para

Template atoms: C1..C6 (C1 bears Br), H7..H11 on C2..C6, Br12. Incoming: C1..C6 (C1 bears N), H7..H11 on C2..C6, N12, H13, H14. Pairs map incoming C1 onto template C4 (para to Br) keeping the same ring sense. Delete template H9 (the H on C4) and incoming atoms 1-11 (its ring and ring H). Product = 11 kept template atoms in template order, then N, H, H. Hand check: N sits 1.40 Å from template C4 along the outward radial direction, i.e. at (0, -2.79, 0); the two N-H point away from the ring in the ring plane.

Expected alignment RMSD over the pairs: 0.000000 Å

Provenance: First principles: idealised benzene ring (C-C 1.39 Å, C-H 1.08, C-Br 1.90, C-N 1.40, N-H 1.01, all planar); incoming aniline built in the template frame then rotated 2.1 rad about (0.3,-1,0.5) and translated by (-4,3,7). Cross-check: an independent textbook quaternion (Horn 1987) fit and the original program's fitting routine agree to 4.5e-15 Å on every moved atom (original RMSD 0.000000 Å).
