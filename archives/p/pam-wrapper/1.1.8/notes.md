# pam-wrapper 1.1.8 adaptation notes

## Scope

- Issue: 1763
- Worktree: `D:\harmonyos\worktrees\pam-wrapper`
- Branch: `feat/pam-wrapper-1.1.8`
- Allowed edit scope: `archives/p/pam-wrapper/1.1.8/`

## W0 dependency check

`pam-wrapper` is a CMake cwrap project for testing PAM applications and PAM
modules. It builds:

- `libpam_wrapper.so`, an LD_PRELOAD interposition library
- `libpamtest.so`, the public C helper API
- PAM test modules such as `pam_matrix.so`
- optional Python bindings when Python development headers are present

The hard dependency is a PAM implementation. Source inspection shows direct
use of `security/pam_appl.h`, `security/pam_modules.h`, `security/pam_ext.h`,
`libpam`, and optionally `pam_misc`. No `linux-pam`, `openpam`, or equivalent
Conan recipe was found under `origin/main` in this repository.

The optional upstream CTest suite also requires `cmocka >= 1.1.0`. The
repository contains `archives/c/cmocka/2.0.2`, but that archive is currently
metadata-only in this checkout and local Windows does not provide `conan`, so
the remote `ohpcd` recipe check could not be run here.

## Source and build analysis

- Source URL: `https://ftp.samba.org/pub/cwrap/pam_wrapper-1.1.8.tar.gz`
- SHA256: `6549c0b3e41d1ebe0c94a1be63c25eec918191462b602ab6f47d4a5fa709c3e4`
- Build system: CMake, top-level `CMakeLists.txt`, minimum CMake 3.20
- Default recipe mode: `UNIT_TESTING=OFF`
- Optional upstream test mode: `-o pam-wrapper/*:with_upstream_tests=True`

Upstream always adds `src/python`; the Python extension target is only built
when CMake finds Python 3.10 development files, so no patch is needed for the
default C/C++ package path.

## Prepared Conan package

The recipe and test package are prepared against the separately adapted
`linux-pam/1.7.2` package.

The consumer test is not an empty smoke test. It:

- builds a C program against `libpamtest.h`
- loads `libpam_wrapper.so` with `dlopen`
- uses a pre-created PAM service file pointing at installed `pam_matrix.so`
- uses a small passdb created before the test process starts
- runs `run_pamtest()` and verifies a successful authentication result

`test_package/test_pam_wrapper.c` was rechecked against the official
`pam_wrapper-1.1.8` sources. In the non-DOXYGEN build path,
`run_pamtest()` is a macro that passes `sizeof(test_cases) /
sizeof(test_cases[0])` to `_pamtest()`, and `src/libpamtest.c` iterates
with `tcindex < num_test_cases`. The single-entry `tests[]` array is
therefore bounded by an explicit count rather than a sentinel.

## Local verification

Performed locally:

- Downloaded the official tarball
- Computed SHA256
- Inspected CMake dependency detection and upstream tests
- Prepared `conanfile.py`, `conandata.yml`, `test_package/`, `manifest.yaml`,
  and reports

Not performed locally:

- `conan download`: `conan` is not installed on this Windows host
- `conan create`: local Windows host has no Conan/OHOS toolchain

## OHOS real-device verification

Device run: `/storage/Users/currentUser/ohos-test-runs/codex-pam-wrapper-pam-wrapper-pam-wrapper-1.1.8-r3-conan5-20260806-132958-13395`

Command shape:

```sh
sh "$HOME/bin/ohos-test-runner.sh" --try-lock \
  --user codex-pam-wrapper \
  --lib pam-wrapper \
  --task pam-wrapper-1.1.8-r3-conan5 \
  --mode heavy \
  --workdir /storage/Users/currentUser/ohos-users/codex-pam-wrapper/pam-wrapper-1.1.8-r3/repo/build_in_harmonyos \
  --path "$HOME/.local/bin:$HOME/usr/local/bin:/data/service/hnp/bin" \
  -- sh /storage/Users/currentUser/ohos-users/codex-pam-wrapper/pam-wrapper-1.1.8-r3/run-pam-wrapper-ci.sh
```

Result:

- L0: pass
- L1: pass, `test_package` executed and printed `pam-wrapper libpamtest authentication check passed`
- L2: skip, no `bin/` directory for this library package
- L4: pass, patch scan clean
- L5: pass, library artifacts present

Portability fixes found during device validation:

- Upstream CMake detection needed Conan-provided PAM include/library paths
  instead of system `pam`/`pam_misc` names.
- OHOS package artifacts need `.so` signing before runtime loading; signing
  tools are resolved from environment/PATH and missing tools fail the package
  step instead of silently skipping signing.
- `pam_wrapper` copies `PAM_WRAPPER_SERVICE_DIR` during `LD_PRELOAD`
  initialization, before `main()`, so the test service/passdb files must be
  created by the Conan test recipe before launching the executable.

## Next steps

Before enabling optional upstream tests, verify:

1. The optional test dependency is available:
   `conan download "cmocka/2.0.2" -r=ohpcd --only-recipe`.
2. Run the optional test variant if needed:
   `conan create archives/p/pam-wrapper/1.1.8 -o pam-wrapper/*:with_upstream_tests=True`.
3. Re-run single-package validation after dependency publication:
   `CI_PACKAGES="archives/p/pam-wrapper/1.1.8" zsh ci/conan/build_and_test.sh`.
