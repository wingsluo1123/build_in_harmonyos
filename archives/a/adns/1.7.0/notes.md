# adns 1.7.0 adaptation notes

- Upstream source: `adns-1.7.0.tar.gz`
- Build system: Autotools
- Upstream regression inventory: 102 files matching `regress/case-*.sys`; count command: `find regress -maxdepth 1 -type f -name 'case-*.sys' | wc -l`.
- Adaptation patch: keep generated regression harness sources in the out-of-source build directory.
- OHOS HMDFS fix: create Autoconf temporary directories with `umask 022` so `config.status` can write its generated AWK scripts.
- `make check` runs in `build()` on OHOS; the generated regression harness omits complete parallel dependencies, so the build and test run are serialized.
- Runtime coverage: IPv4 text/address conversion, port preservation, insufficient-buffer handling, invalid-address handling, and status-string lookup.
- The upstream runner emits per-case `UPSTREAM-PASS` / `UPSTREAM-SKIP` / `UPSTREAM-FAIL` / `UPSTREAM-NOTRUN` lines and a single `UPSTREAM-SUMMARY` line.
