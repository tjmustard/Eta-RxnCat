# 02_quarter_turn

Hand check: a +90 degree turn about z through the origin maps incoming (1,0,0)->(0,1,0) and (0,1,0)->(-1,0,0), i.e. exactly onto the template; both centroids coincide after the turn, so no net translation. The Cl on the z axis stays at (0,0,1). Product = 3 template atoms then Cl.

Expected alignment RMSD over the pairs: 0.000000 Å

Provenance: First principles: incoming triangle is the template turned -90 degrees about +z; the Cl on the z axis is unaffected by the turn. Cross-check: an independent textbook quaternion (Horn 1987) fit and the original program's fitting routine agree to 4.7e-16 Å on every moved atom (original RMSD 0.000000 Å).
