# vapoursynth 74 adaptation notes

## Scope

- Target package: `vapoursynth/74`
- Branch: `feat/vapoursynth-74`
- Issue: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/1456
- Upstream release: VapourSynth R74 / PyPI version 74.
- Source URL: `https://files.pythonhosted.org/packages/ca/b8/bb874a0147c66f7339be68477a81f81cd94d6ab4fe77d2bde635120d4e5d/vapoursynth-74.tar.gz`
- Source sha256: `8d758c296dd87329b131dbb718350c17c117ef59a125376dcb49b5e3a2dfaa24`
- Related upstream tag check: GitHub codeload tag `R74` downloaded locally with sha256 `9ebf49720a48a6b5e4abdfd969f318545dde82d67f3e3c68a0799371333d96be`.

## W0 dependency check

Required for the core library:

- `zimg/3.0.6` (satisfies upstream `zimg >= 3.0.5`)

Required for upstream test execution in this recipe:

- Python >= 3.12 runtime for the packaged Python module.
- Cython >= 3.1 for building the Python module.

Local/remote status:

- `zimg/3.0.6` was merged to `origin/main` by `e4d4a930a31fbd8eeeefd1ad14345fe64fc4a3a7` (`【依赖项】feat(zimg) 3.0.6`) and is associated with issue #1459.
- Formal CI on 2026-08-04 resolved and downloaded `zimg/3.0.6` from `ohpcd`.
- After rebasing this branch to latest `origin/main` and exporting `archives/z/zimg/3.0.6` as `zimg/3.0.6`, `conan install` resolves the zimg recipe from local cache.
- The same `conan install ... --build=never` then stops at the expected missing binary for OHOS/armv8: `Missing binary: zimg/3.0.6:01d92cf349a0dd98ff915f4bd99a04430171517f`.
- Formal CI provides a Python 3.12 runtime for Cython and test execution, but it does not guarantee a linkable `libpython3.12.so` development library in the path reported by `sysconfig`.
Conclusion: the old missing-recipe blocker is cleared in git. Python/Cython is handled in this recipe for the upstream test path, and the Python extension must link against an actually existing libpython path rather than trusting a single `sysconfig` libdir.

## Source/build-system analysis

- Build system: Meson. Upstream declares `c`, `cpp`, and `cython`; this recipe patches Meson so Cython is only required when the Python module is enabled.
- Default upstream options build core and VSScript, while `vspipe` and the Python module are force-disabled unless `build_wheel=true`.
- Core library builds `libvapoursynth` and installs public headers plus `vapoursynth.pc` when `build_wheel=false`.
- Core links `zimg` statically through Meson dependency lookup and also uses threads and `dl` on non-Windows platforms.
- Upstream test directory contains 12 Python files. Eleven are `unittest` modules covering the Python runtime and filters; `expr_compiler/compiler_test.py` is a harness around upstream `src/core/expr/main.cpp` (`ExprDebugger.exe`).

## Recipe strategy

- Use MesonToolchain + PkgConfigDeps.
- Require `zimg/3.0.6` explicitly; do not use Meson wraps or vendored fallback.
- Disable x86 asm for HarmonyOS/armv8.
- Disable VSScript and vspipe by default; enable and package the Python module by default so upstream Python tests run in `test_package`.
- Install or reuse `Cython >= 3.1`, inject a Conan Meson native-file `cython` wrapper, and build the OHOS Python extension by probing real libpython candidates from `sysconfig`, the Python executable prefix, and OHOS runner locations before adding `link_args`.
- Patch Meson so disabling the Python-related options still skips unconditional Python/Cython probing when `python_module=False`.
- Provide a non-empty C consumer test that links against `libvapoursynth`, checks `getVapourSynthAPI`, verifies API version, and creates/frees a `VSCore`.
- Package upstream Python tests plus the upstream expression debugger source. `test_package` compiles an OHOS `ExprDebugger.exe`, runs all 11 upstream unittest modules, and then runs `expr_compiler/compiler_test.py` through the compiled debugger.

## Next verification commands

After `zimg/3.0.6` is available in the runner cache/remote, or when the runner is allowed to build missing dependencies:

```sh
cd D:/harmonyos/worktrees/vapoursynth
conan create archives/v/vapoursynth/74 --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

Single-package CI/shadow command from repository root:

```sh
CI_PACKAGES="archives/v/vapoursynth/74" zsh ci/conan/build_and_test.sh
```

Shadow CI runner form:

```sh
/path/to/run-ohos-shadow-ci.sh archives/v/vapoursynth/74
```

## Current blocking points

- Formal CI now resolves `zimg/3.0.6` from `ohpcd`.
- The 2026-08-04 formal CI failure was caused by the previous patch forcing `-lpython3.12` with a single `sysconfig` libdir when linking `vapoursynth.abi3.so`; the CI Python runtime did not provide a matching linkable libpython in that location. This revision probes for an existing libpython path before adding Python extension link args.

## True-device validation

- Device job: `/storage/Users/currentUser/ohos-users/codex-vapoursynth/vapoursynth-74-20260728-r1`
- Latest passed run: `/storage/Users/currentUser/ohos-test-runs/codex-vapoursynth-74-vapoursynth-74-20260728-r1-conan-20260804-131200-51092`
- Command: `sh "$HOME/ohos-users/codex-vapoursynth/vapoursynth-74-20260728-r1/run-conan-heavy.sh"`
- Result: pass. `vapoursynth/74` built, packaged `libvapoursynth.so.4`, copied `libvapoursynth.so` for consumers on non-symlink platforms, executed the direct C smoke test, and covered all 12 upstream Python test files: 11 unittest modules / 157 cases (`Ran 157 tests in 85.866s`, `OK`) plus `expr_compiler/compiler_test.py` / 69 expressions.
- Summary: `L0_RESULT=pass`, `L1_RESULT=pass`, `L2_RESULT=skip` (no `bin/`), `L4_RESULT=pass`, `L5_RESULT=pass`, `Success: 1`, `Failed: 0`.
