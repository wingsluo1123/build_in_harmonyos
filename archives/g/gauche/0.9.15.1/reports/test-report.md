# Test Report - Gauche 0.9.15.1

## Dependency Publication Preflight

- Command: `bash ci/scripts/preflight_check.sh gauche/0.9.15.1`
- Result: PASS. The recipe declares no Conan requirements, so there are no
  unpublished declared dependencies to block this package.

## Source Verification

- Source: `https://practical-scheme.net/vault/Gauche-0.9.15.tgz`
- SHA-256: `3643e27bc7c8822cfd6fb2892db185f658e8e364938bc2ccfcedb239e35af783`
- Result: PASS. The official Gauche archive matched the declared checksum.

## Final Recipe Build

The final recipe uses the official release archive and standard
`apply_conandata_patches(self)`. The source-only 0046/0047 patches update
`configure.ac` inputs and Autoconf regenerates both configuration scripts;
the recipe does not edit generated `configure` or `Makefile.in` files. It
builds only the upstream `gc`, `src`, and `lib` core subdirectories, because
OHOS cannot load the optional `ext` modules correctly.

- Command: `conan create archives/g/gauche/0.9.15.1 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable`
- Result: PASS. `finish` recorded W3 success at `2026-08-13T11:31:52` with
  exit code `0` in `.ci-result.json`.
- Build result: the core interpreter and shared library compiled successfully
  from the official archive with the OHOS profile.
- Installation result: `gosh`, `libgauche-0.98.so`, public headers, and Scheme
  standard-library files were packaged from completed core build artifacts.
- Consumer test: `test_gauche` compiles against `gauche.h` and `libgauche`,
  initializes the runtime, and asserts that `(+ 1 2 3)` evaluates to `6`.
- Interpreter smoke test: the packaged `gosh` evaluated `(+ 1 2 3)` to `6`.

## Runtime Environment

`package_info()` provides `GAUCHE_LOAD_PATH` for the packaged Scheme standard
library. GNU Make uses `--jobserver-style=pipe` because HMDFS forbids its
default FIFO jobserver implementation.

## Upstream Test Scope

`make check` is not integrated into the final recipe. The skipped `ext`
directory means the complete upstream suite cannot run: standard modules such
as `gauche/uvector` and `gauche/unicode` are not packaged. This limitation must
remain explicit in any future PR description.
