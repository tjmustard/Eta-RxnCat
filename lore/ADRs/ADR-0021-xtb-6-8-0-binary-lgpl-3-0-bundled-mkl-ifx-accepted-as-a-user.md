Decision (TJ, 16:24Z, verbatim "Q2. A", row qitem-20261122162111-26e232a707f003e2; resolve R12; Red Team F12). Eta-RxnCat uses the official xtb 6.8.0 x86_64 binary as a user-downloaded subprocess engine. Its licence is LGPL-3.0, with Intel MKL and the ifx runtime (proprietary) statically linked.

Provisioning:
- asset xtb-6.8.0-linux-x86_64-ifx-mkl.tar.xz;
- GitHub digest sha256 db090333361749ae0d9ccf0ce7c0035c0000f2ebad0847f6d77191d1954f4d68, 22,686,860 B;
- installed under ~/.local/share/eta-rxncat/xtb/6.8.0/, outside the repo;
- `xtb --version` recorded.
The release's .sha256 file names it xtb-bleed-…, which is recorded as a provenance note.

It is never vendored and never runs in-process. It is recorded in docs/licence-inventory.md, which also covers model weights. Building from source with OpenBLAS was the rejected alternative.
