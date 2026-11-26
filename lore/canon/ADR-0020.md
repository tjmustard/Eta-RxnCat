Decision (TJ, 16:24Z, verbatim "Q1. A", row qitem-20261122162111-26e232a707f003e2; resolve R1; Red Team F1). The GPU and MLIP stack moves to torch 2.13 +cu129 (index pytorch-cu129), with fairchem-core >= 2.22. That gives native uma-s-1p2p1, the plan's uma-s-1.2.1. The cu128 line was capped at torch 2.11 there, and fairchem 2.21 does not know uma-s-1p2p1.

Resolve's scratch `uv lock` resolved torch 2.13.0+cu129, fairchem-core 2.26.0, mace-torch 0.3.17 and nvidia-cusolver-cu12 11.7.5.82, and dropped ray and ray-haproxy.

Consequences:
- v0.1.0's GPU acceptance is re-proved on the new stack under R49, recording the mapped cuSOLVER.
- All four licence profiles are re-run.
- NVIDIA CUDA packages without the nvidia- prefix, or with unrecognised metadata, are exempted version-pinned under TJ v0.1.0 Q1 A; anything else is reported.

Amends ADR-0008's "+cu128" wording for the torch index. The 6.5 GiB budget is unchanged.
