# vlang 0.5.2

V is a self-hosted compiler and toolchain. The upstream Makefile normally
downloads or updates `vc/v.c` from `vlang/vc` before building. This recipe
downloads the `v` release tarball and the `vc` bootstrap tarball in `source()`,
then runs only the local `make v` bootstrap target.

The contest issue name is `v`, but the Conan recipe name is `vlang` because
Conan 2 rejects single-character package names.

## Scope

- Build the `v` compiler from `vc/v.c`.
- Package the real compiler under `share/v/v` with `cmd`, `vlib`, and
  `thirdparty` beside it.
- Install `bin/v` as a wrapper so the compiler can discover its source root.
- Do not run upstream `v test-all` in the first package because it fans out into
  thousands of compiler, vlib, formatter, documentation, examples, and tooling
  checks.

## Test Inventory

- `_test.v` files in the 0.5.2 release tree: 3415.
- `.vv` compiler/input test fixtures: 2473.
- `.out` expected-output fixtures: 2016.
- Example `.v` programs: 338.
- `cmd/tools` `.v` sources: 195.

The first `test_package` compiles and runs a small V program through the
installed wrapper. Full upstream `v test-all` remains pending OHOS target/CI.

## Local Validation

- `python -B -m py_compile` passed for the recipe and test recipe.
- `git diff --check` passed.
- Windows native `conan create vlang/0.5.2` passed with Conan 2.30, MinGW GCC
  8.1, `mingw32-make`, and Git for Windows POSIX shell tools.
- `test_package` ran `v version`, compiled `test_v_language.v`, executed the
  generated program, and printed `v-test-package-ok`.
- OHOS target-profile validation and full upstream `v test-all` remain pending
  an OHOS/OpenDesk host or CI.
