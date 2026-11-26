Decision (resolve, v0.2.0, R5; Red Team F5). An MLIP engine's `EngineIdentity.model` is `"<name>@sha256:<64 hex>"`. The hash is computed from the weights file at construction, before the weights are loaded. MACE additionally checks the hash against a pinned value:
- MACE-MP-0 medium = 2023-12-03-mace-128-L1_epoch-199.model;
- sha256 01bfe22100139f424713cf921144e5509cbe353d67aa9fa1be9c6e1e0ed35845;
- MIT.
It refuses a mismatch before torch-loading the pickle.

UMA's hash is recorded at first load, because the gated repo masks the LFS oid. Engines never download implicitly. Neither paths nor tokens enter the identity.

Trade-off: a name-only identity or an HF revision was rejected. A re-upload under the same name, or a replaced local file, would silently reuse cache entries (ADR-0001: a wrong cache hit is a silent scientific error). The cost is hashing a 2.3 GB file once per engine construction.
