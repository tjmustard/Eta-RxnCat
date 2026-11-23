# 06_degenerate_pairs

Provenance: first-principles inputs; original-program behaviour observed by running its fitting routine.

Three cases on these files, none of which has a unique answer:

- A. one pair (template 1 <- incoming 1): after centring both point sets are a single point at the origin; the rotation is completely undetermined. The original program fails with an unhandled arithmetic error (division by zero) and writes no product.
- B. two pairs (1<-1, 2<-2), or C. three collinear pairs (1<-1, 2<-2, 3<-3): translation and the axis direction are determined, but any spin about that axis fits equally well (RMSD 0). The original program returns one arbitrary spin; for these exact inputs it turns the spectator O from (0,1,0) to (0,-1,0) even though leaving it in place is equally optimal. With other geometries of the same kind (e.g. two template points along x paired with two incoming points along z) it instead crashes with the same division by zero.

Expected behaviour for a reimplementation: refuse (or at least flag) any pair set with fewer than 3 points or whose points are collinear within tolerance, rather than returning an arbitrary orientation. No expected_product.xyz is given on purpose.
