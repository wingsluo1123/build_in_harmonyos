# raidtest 1.3 — HarmonyOS PC adaptation notes

## What it is

`raidtest` is the FreeBSD storage-device benchmark from
`benchmarks/raidtest` (BSD-2-Clause, Pawel Jakub Dawidek). It generates a
file of random I/O requests (`genfile`) and replays them against a block
device with N parallel processes (`test`), reporting bytes/requests per
second. Upstream version 1.3, package version 1.3 — no increment needed.

## W0 dependency audit

- Runtime deps: none (libc only; POSIX APIs: fork/wait/kill/pread/pwrite/
  arc4random/err/getopt).
- Build deps: a C compiler (Conan-provided).
- Test deps: `sh` and `python3` (both present in the Conan runner).
- Conan dependencies: none. No split-PR needed.

Conclusion: W0 clean, no blocking dependency.

## Source acquisition

There is no upstream release tarball (the port sets MASTER_SITES=none); the
sources live inside the ports tree itself. `source()` therefore downloads
`raidtest.c` and `README` individually at a fixed commit (`86b2c512`), each
with a pinned SHA256 (see manifest.yaml), trying two mirrors of the same
commit in order:

1. codeberg.org (FreeBSD ports git mirror) — primary; **rate-limits shared
   CI egress IPs with HTTP 429** (observed on platform CI build #79817);
2. raw.githubusercontent.com/freebsd/freebsd-ports (official GitHub mirror
   at the identical commit; both files SHA256-verified identical).

Deliberate choices:
- **No `conandata.yml`** — avoids the CI pre-download path with the
  uninitialized `BUILD_DIR`, and per-file `download()` involves no archive
  format inference (no BadZipFile risk).
- **The ports `Makefile` is not packaged or used** — it is a bsd.port.mk
  backend fragment (USES=uidfix) that only works inside the ports
  framework. `build()` compiles the single translation unit directly.

## W1 source analysis

Single ~430-line C file. Portability review against musl/OHOS (confirmed by
cross-compiling with the OHOS SDK aarch64 sysroot — see W4):

| Upstream construct | musl/OHOS status | Action |
|---|---|---|
| `<sys/endian.h>` (le64enc/le64dec/...) | FreeBSD-only header, and musl `<endian.h>` lacks the leNNenc/leNNdec helpers | patch: `<endian.h>` + static inline byte-wise helper implementations on `__linux__/__OHOS__` |
| `#if __FreeBSD_version < 500028` | undefined → treated as 0 → FreeBSD 4.x compat block wrongly enabled (uintmax_t typedef redefinition) | patch: `defined(__FreeBSD__) &&` guard |
| `getprogname()` | present in glibc-style musl but **not declared** by the OHOS musl headers | patch: static fallback on non-FreeBSD |
| fork loop writes `procs[i]` while iterating `j` | upstream typo → out-of-bounds write for `-n > 1` | patch: `procs[j]` |
| `arc4random()` | provided by the OHOS musl sysroot | none |
| `err/errx` (`<err.h>`) | provided by musl | none |
| `O_DIRECT` | defined by musl (open may still fail on some filesystems — handled by tests as an error path) | none |
| `timersub`, `struct timeval` | POSIX/musl | none |

Known upstream doc staleness (recorded, not patched): the ports `README`
documents a `-R` option that the 1.3 code does not implement.

Test audit: the port ships no test suite; validation is provided by the
Conan test_package (13 assertions). The device `test` subcommand needs a raw
block device and is covered only through argument-validation error paths; a
real throughput run on a device is a manual post-merge option.

## W4 local verification (Windows host)

- `conanfile.py` / `test_package/conanfile.py` compile-checked (`py_compile`).
- `manifest.yaml`, `test_package/MANIFEST.yml` YAML-parsed.
- Full patch set applied and cross-compiled with the OHOS SDK clang
  (`--target=aarch64-linux-ohos --sysroot=<SDK>/sysroot -O2 -Wall`):
  exit 0, zero warnings, `llvm-readelf -h` reports AArch64 OHOS ELF, and the
  only `NEEDED` entry is `libc.so`.
- Initial naive patch set (endian include only) failed the cross-compile
  with typedef-redefinition errors — kept as evidence of why the full patch
  set is required.
- The packaged binary cannot execute on the Windows host (aarch64 OHOS ELF);
  running test_package therefore happens on the device (shadow CI).

## W5 device shadow CI (executed)

Isolated job on the HarmonyOS PC device (aarch64, OHOS toolchain), package
`archives/r/raidtest/1.3`, runner `run-conan-heavy.sh` under the global
device lock. Final round (r3): exit code 0.

```text
L0_RESULT=pass
L1_RESULT=pass  (includes L1e destructive negative test: confirmed the
                 test genuinely depends on the packaged binary)
L2_RESULT=skip: raidtest version/help failed (raidtest has no --version or
                 --help option by design; non-blocking smoke skip)
L4_RESULT=pass
L5_RESULT=pass  (bin/ has content)
test_package: 15 passed, 0 failed
conan create: Success 1 / Failed 0 (100%)
```

Iteration log:
- r1 exit 1 — test_package could not receive `CONAN_TEST_PACKAGE_BIN`
  through the Conan runenv on the device runner; all build stages had
  already passed. Fix: hand the bindir over as an explicit argv.
- r2 exit 1 — 14/15: the `-f` overwrite check reused `data.bin` and broke
  the later record-count expectation (test-script bug, not a portability
  issue). Fix: dedicated `ow.bin` for the overwrite check.
- r3 exit 0 — all gates pass (results above).
Platform CI note: build #79817 failed in source() with codeberg HTTP 429
(rate limiting of the shared worker egress IP), not a test failure - L0/KC/JC
had all passed before the download. Fix: per-file mirror fallback
(codeberg -> GitHub ports mirror, same commit, identical SHA256).

## Verification commands

```sh
# local cross-compile check (Windows host, OHOS SDK clang)
clang --target=aarch64-linux-ohos --sysroot="$OHOS_SDK/native/sysroot" \
  -O2 -Wall patched_raidtest.c -o raidtest

# recipe/test syntax
python -m py_compile archives/r/raidtest/1.3/conanfile.py \
  archives/r/raidtest/1.3/test_package/conanfile.py

# consumer tests (device)
CONAN_TEST_PACKAGE_BIN=<package>/bin sh archives/r/raidtest/1.3/test_package/test.sh
```
