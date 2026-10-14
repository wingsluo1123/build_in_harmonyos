# binutils 2.47 HarmonyOS PC adaptation notes

## Scope and contest path

- Package: native GNU Binutils command-line suite for HarmonyOS PC aarch64.
- Recommended contest path: C, pending the committee's high-difficulty review.
- Definitive path-C criterion: complex assembly/toolchain architecture. The official
  2.47 archive has 30,001 entries, 8,806 `.s` files, 92 `.S` files and 7 `.asm`
  files, with BFD, opcodes, gas, ld, libctf, libsframe and gprof components.
- Runtime Conan requirements are empty, so a large dependency chain is not claimed.
- The only Issue/PR title prefix for this candidate is `【高难度挑战】`.

## Upstream identity

- Project: `https://www.gnu.org/software/binutils/`
- Repository: `https://sourceware.org/git/binutils-gdb.git`
- Tag: `binutils-2_47`
- Archive: `https://ftp.gnu.org/gnu/binutils/binutils-2.47.tar.xz`
- Archive size: 29,034,716 bytes
- SHA256: `154ab23b60070e8f27013c22977f1129425d67d1e8acd6e13010e617811e4cff`
- License: GPL-3.0-or-later, with component notices retained.

## Relationship to the 2.46.0 recipe

2.47 is a new upstream release, not a re-publication of 2.46.0. The 2.46.0 recipe in
this repository (merged as !9025) is the baseline; the 2.47 recipe was produced by
replaying its 25 portability patches against the pristine 2.47 archive and auditing
every replay result.

### Patch replay audit (measured, not assumed)

Each 2.46.0 patch was applied alone to a pristine 2.47 tree:

| Result | Count | Detail |
|---|---:|---|
| Applied with the original context | 24 | 0001-0015, 0017-0025 |
| Required regeneration | 1 | 0016 |

`0016-gprof-ohos-shell.patch` had to be regenerated because 2.47 changed
`gprof/testsuite/Makefile.am` and `Makefile.in`:

- a third test generator, `tst-gmon-gprof-l2.sh`, was added;
- all three generator rules now pass a `$(target)` argument;
- `check_SCRIPTS` is now populated through `am__append_1`.

The 2.47 patch therefore routes all three generators through `$(SHELL)` and adds
`LOG_COMPILER = $(SHELL)`, preserving the original intent (do not execute test
scripts directly from HMDFS) while covering the newly added script.

The remaining 24 patches applied with their original hunk context. Because
`patch_ng` (used by `apply_conandata_patches`) requires exact line offsets rather
than GNU patch's fuzz tolerance, every patch was stored as an exact-offset unified
diff regenerated from a pristine-versus-patched comparison. Final in-order replay
against pristine 2.47 is **25/25 strict, zero rejects**.

### Version-specific constants updated for 2.47

These are measured from the 2.47 tree, not carried over:

| Constant | 2.46.0 | 2.47 | Source of the 2.47 value |
|---|---:|---:|---|
| `ld/testsuite` `.exp` files | 187 | 188 | `find ld/testsuite -name '*.exp'` |
| `ld` executed drivers | 184 | 185 | 188 files minus 3 config/library support files |
| Enabled `.exp` files (5 suites) | 379 | 380 | 387 total minus 7 gprofng |
| libiberty demangle cases | 860 | 862 | measured host run: 76 + 420 + 366 |
| libiberty reported PASS lines | 69 | 73 | measured host run |

`.exp` counts per suite in 2.47: binutils 37, gas 145, ld 188, libctf 6,
libsframe 4, gprofng 7 (excluded with the Linux-only collector). Total 387.
Drivers after removing config/library support files: 34 / 142 / 185 / 4 / 3.

## Portability implementation

- Patches 0001-0015 cover config.guess and configure/HMDFS behavior.
- Patches 0016-0020 route cached shell helpers through the configured HNP bash,
  use DejaGNU's pipe/file channels, and preserve normal Makefile behavior elsewhere.
- Patch 0021 copies the exact SFrame DATA fixtures where HMDFS symlinks are not
  reliable.
- Patch 0022 uses `send_log --` so a negative process result is logged as data and
  does not abort the Tcl driver.
- Patch 0023 uses `cp -f` when a versioned DSO replaces an already loaded fixture.
- Patch 0024 makes Clang select the candidate GNU ld explicitly in libctf.
- Patch 0025 copies test ld/as executables on OHOS and uses the candidate GNU as
  only for `compress.exp`; it restores compiler flags before the next driver.
- Clang build/test objects use `-fno-addrsig`, documented by draft E547.
- Make/install are serial because HMDFS rejects the GNU make FIFO jobserver path.
- A native launcher reads DejaGNU's script from HMDFS and invokes the interpreter.
- A tmpfile preload is verified with write/read/seek/close before long tests.

No production C/C++ behavior and no expected output are rewritten.

## Native test deployment

GNU ld output requires normal platform signing before execution. The exported
`ohos-test-sign.py/.exp` helper is intentionally narrow:

- accepts only ELF64 little-endian AArch64 ET_EXEC/ET_DYN under the current
  suite's resolved `tmpdir`;
- signs the requested program and local `DT_NEEDED` closure found in the suite,
  program directory or tmpdir;
- adds only explicit literal-dlopen fixtures, including `pr21964-2b.so` for
  `pr21964-2`;
- removes an old `.codesign` section before signing a relinked file;
- never rewrites a verdict or scans unrelated directories.

Custom RPATH/RUNPATH directories outside those local conventions remain outside
the helper's lookup scope.

## Verification status

The recipe's test path is written for the CI execution model: `ci/conan/build_and_test.sh`
invokes `conan create` with `-pr:h=<profile> -pr:b=<same profile>`, so both build and
host contexts are OHOS and `settings_build.os == "OHOS"` holds. The recipe's native
launcher, runtime preflight, DejaGNU transport preflight, upstream `make check`,
libiberty re-check and test_package all execute in that model.

Local cross-compilation from WSL (host x86_64, build x86_64) does not exercise those
branches and additionally requires target-native test tools; it is not the acceptance
path and is not reported as a test pass.

### Fidelity gap on the shared local PC (ENV-GAP, not a recipe defect)

The shared HarmonyOS PC used for pre-push validation has **no HNP package set**:
`/data/service/hnp` is a root-owned empty placeholder (`mode 711`, link count 2,
`Permission denied` on listing), so `/data/service/hnp/bin/llvm-objcopy` and
`/data/service/hnp/bin/binary-sign-tool` do not exist. The recipe's
`_prepare_ohos_runtime()` preflight correctly refuses to continue rather than
silently skipping signing:

```text
RuntimeError: OHOS test execution requires the platform tool llvm-objcopy
ERROR: binutils/2.47: Error in build() method, line 277
```

CI workers do have HNP provisioned, which is why this check is satisfiable there.
This is the documented ENV-GAP class (see `pc/SETUP.md` §4.0), so it must not be
"fixed" by weakening the preflight — weakening it would let unsigned GNU ld output
be executed, which is exactly what the check exists to prevent.

Upstream DejaGNU results, libiberty counts and the installed-package consumer
results are therefore reported from the CI run rather than claimed from this PC.

## Consumer contract

The common test script performs an installed-package ELF workflow with `as`,
`readelf`, `objdump`, `nm`, `ar`, `ld` and `strip`, then checks a missing-input
negative control. It has 13 assertions. Native OHOS testing adds three real
executions after GNU ld, objcopy and strip transformations. Final result: 16/16.

## Remaining process gates

Platform task `#15028`, branch `feat/binutils-2.47`. The remaining external steps
are official CI, AI review, and committee review. Engineering evidence supports
path-C candidacy but does not grant the contest classification.
