# 05_planar_reversed_order

For a planar alignment set, walking one ring backwards is still reachable by a proper rotation (a 180 degree flip about an in-plane axis), so RMSD is still ~0 and nothing warns. The ring lands on the template but the incoming fragment is flipped through the ring plane. Observable result: the product has the same set of positions as 04, but the two amine hydrogens (product atoms 13 and 14) have exchanged places. For a non-planar substituent the fragment would be placed as its mirror image across the ring plane. Shows that RMSD alone cannot detect a reversed mapping on a planar core.

Expected alignment RMSD over the pairs: 0.000000 Å

Provenance: Same structures as 04; pair order walks the incoming ring the opposite way. Expected coordinates obtained by running the fit. Cross-check: an independent textbook quaternion (Horn 1987) fit and the original program's fitting routine agree to 2.5e-15 Å on every moved atom (original RMSD 0.000000 Å).
