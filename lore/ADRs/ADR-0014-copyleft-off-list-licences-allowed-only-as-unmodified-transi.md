Decision (TJ, 14:49Z, "A", row qitem-20261122134346-2d0f88234113eb85; resolve R48). This extends ADR-0010 (Q1 A), and its mechanism is ADR-0013.

TJ, verbatim: "I don't mind the project having people Download GPL or copy left codes for certain steps. I just don't want the code in this project to be copyleft."

The rule:
- Copyleft (GPL, LGPL, MPL) and off-list licences are allowed only as downloaded, unmodified, transitive dependencies of the optional MLIP extras (`mlip-mace`, `mlip-uma`).
- They are never in the `base` or `gpu` install.
- They are never vendored or copied into the repo, and never imported by `eta_rxncat`.
- Eta-RxnCat's own code stays MIT.

Every such package is a version-pinned exemption, scoped to its profile, and records its licence, its parent, the reason and this decision. A new or upgraded package fails the gate until it is reviewed. The list includes, among others:
- GPL: python-hostlist (MACE), ray-haproxy (UMA)
- LGPL: ase, matscipy, psycopg2-binary, ase_db_backends
- MPL-2.0: certifi, tqdm, orjson
- OpenLDAP: lmdb
- MIT files with unparseable metadata: torch-ema, clusterscope

Guards: an AST import ban and a no-direct-dependency check cover every copyleft-exempted distribution. Zlib and CC0-1.0 (numpy, core) are confirmed permitted.
