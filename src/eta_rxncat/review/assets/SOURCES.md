# Vendored review-bundle assets

`eta-view.js` is eta's own (MIT). The other two files are 3Dmol.js 2.5.5, copied unmodified from
the npm tarball. No Python module imports them; they are only copied into a review bundle.

| Item | Value |
|---|---|
| Package | `3dmol` 2.5.5 (published 2026-05-22) |
| Tarball | <https://registry.npmjs.org/3dmol/-/3dmol-2.5.5.tgz> |
| Retrieved | 2026-11-26 |
| Tarball integrity (`npm view 3dmol@2.5.5 dist.integrity`) | `sha512-kqNHouGqq3YfW58174tdERvm0XYTmP0tavQKOqIw1ouc2OJ7epkXEFrtEkVXV0clBZT2Ze2xHRC/qxX0u0qCdw==` |
| `3Dmol-min.js` (`package/build/3Dmol-min.js`, 537792 bytes) sha256 | `f7cc78921ae72e7623e89cdd111434f58c2efddd2ffda1cd212644b406fb8016` |
| `LICENSE-3Dmol.txt` (`package/LICENSE`) sha256 | `4c6eaaed856f3f28a3b1a98e74f4a8a71618de7d51ea4155c29f6f793bcef861` |

## Licence inventory

3Dmol.js is BSD-3-Clause (`LICENSE-3Dmol.txt`, which also carries the licence text of the code it
incorporates). Components in the minified file:

| Component | Licence | Notes |
|---|---|---|
| 3Dmol.js | BSD-3-Clause | University of Pittsburgh and contributors |
| GLmol | MIT or LGPL-3.0 (dual) | **eta elects MIT** |
| three.js | MIT | |
| jQuery | MIT | |
| iobuffer | MIT | runtime dependency |
| netcdfjs | MIT | runtime dependency |
| upng-js | MIT | runtime dependency |
| pako | MIT AND Zlib | runtime dependency |

The minified file contains download URLs (RCSB, PubChem); the bundle page's policy
`connect-src 'none'` blocks them.
