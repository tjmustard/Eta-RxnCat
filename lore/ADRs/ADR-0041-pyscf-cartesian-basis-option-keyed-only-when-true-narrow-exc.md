Decision (resolve, v0.5.0 replan 2, mission R30). The `pyscf_gpu_cpu` engine takes a keyed option `cartesian_basis` (bool, default False). When it is True, every PySCF Mole for the stage is built with Cartesian basis functions (`mol.cart = True`). It exists to reproduce Gaussian references computed with 6D, which is Gaussian's default for the Pople 6-31G family.

Key rule, a narrow exception to ADR-0016 ("every keyed option is filled with its default"): the option appears in the resolved stage only when it is True. The engine removes it when False, so the default and an explicit False key the same. Every PySCF resolved stage and cache key that existed before the option stays byte-identical, and `ENGINE_IMPL` stays 2. An absent key means spherical, permanently. Making True the default would need an `ENGINE_IMPL` bump.

Refused: `init_guess="atom"` together with `cartesian_basis=True`, on both devices, because GPU4PySCF 1.9.2 asserts on that combination and ADR-0018 keeps one stage per device pair.

Limits: the option is Cartesian for every angular momentum. It matches Gaussian only where every shell present was Cartesian there too (d-only Pople bases at 6D), not Gaussian's 6D 7F with f functions.

Trade-off: a plain always-keyed option was rejected, because it changes every existing PySCF key and orphans the v0.2.0–v0.4.0 rows. An `ENGINE_IMPL` bump was rejected for the same invalidation with no gain. Running raw PySCF in the acceptance test was rejected, because R9 requires eta's engine.
