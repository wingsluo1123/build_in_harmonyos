# pam-wrapper 1.1.8 W0 and source-analysis report

## W0 result

Status: dependency resolved with separately adapted `linux-pam/1.7.2`.

`pam-wrapper` requires a PAM implementation at build and runtime:

- headers: `security/pam_appl.h`, `security/pam_modules.h`,
  `security/pam_ext.h`
- libraries: `libpam`, optionally `pam_misc`

No PAM implementation recipe was present in this repository checkout during the
initial W0 pass, so `linux-pam/1.7.2` was adapted first under issue #1765 and is
now used as the hard dependency for this package.

Optional upstream tests require `cmocka >= 1.1.0`. `archives/c/cmocka/2.0.2`
exists, but in this checkout it contains only metadata files and is marked
`partial`; remote availability must be checked on the OHOS/shadow worker before
enabling `with_upstream_tests=True`.

## Source analysis

- Upstream tarball:
  `https://ftp.samba.org/pub/cwrap/pam_wrapper-1.1.8.tar.gz`
- SHA256:
  `6549c0b3e41d1ebe0c94a1be63c25eec918191462b602ab6f47d4a5fa709c3e4`
- Build system: CMake
- Main options: `UNIT_TESTING`, `PICKY_DEVELOPER`
- Default prepared package mode: `UNIT_TESTING=OFF`

Important files inspected:

- `CMakeLists.txt`: top-level CMake project and CTest/cmocka hook
- `ConfigureChecks.cmake`: PAM header/library and libc capability checks
- `src/CMakeLists.txt`: builds `pam_wrapper` and `pamtest`
- `src/modules/CMakeLists.txt`: builds `pam_matrix`, `pam_get_items`,
  `pam_set_items`, and `pam_chatty`
- `src/python/python3/CMakeLists.txt`: Python extension is conditional on
  Python development files
- `tests/CMakeLists.txt`: registers cmocka and Python tests when enabled

## Prepared artifacts

- `conanfile.py`
- `conandata.yml`
- `test_package/conanfile.py`
- `test_package/CMakeLists.txt`
- `test_package/test_pam_wrapper.c`
- `test_package/MANIFEST.yml`
- `manifest.yaml`
- `notes.md`

The test package performs a real consumer exercise: it pre-creates a
`pam_matrix` service and passdb, loads `libpam_wrapper.so`, and calls
`run_pamtest()` from `libpamtest`.

## OHOS real-device result

Run:
`/storage/Users/currentUser/ohos-test-runs/codex-pam-wrapper-pam-wrapper-pam-wrapper-1.1.8-r3-conan4-20260806-014917-45723`

- L0: pass
- L1: pass, `test_package` executed and printed
  `pam-wrapper libpamtest authentication check passed`
- L2: skip, no `bin/` directory
- L4: pass, patch scan clean
- L5: pass, library artifacts present

Runtime note: `pam_wrapper` copies `PAM_WRAPPER_SERVICE_DIR` during
`LD_PRELOAD` initialization, before `main()`, so test service files are created
by `test_package/conanfile.py` before launching the executable.

The verification job used a clean `main` clone where `linux-pam/1.7.2` is
tracked by the repository; no local `conan export archives/l/linux-pam/1.7.2`
step was used.

## Next commands

Run after `linux-pam/1.7.2` is available in the target Conan remote/cache:

```sh
conan download "cmocka/2.0.2" -r=ohpcd --only-recipe
CI_PACKAGES="archives/p/pam-wrapper/1.1.8" zsh ci/conan/build_and_test.sh
```

Shadow CI equivalent:

```sh
/path/to/run-ohos-shadow-ci.sh archives/p/pam-wrapper/1.1.8
```
