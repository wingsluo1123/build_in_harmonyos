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
- Disable VSScript and vspipe by default. The Python binding stays off by default too (`python_module=False`), because the CI worker can neither build nor load it (see the E212 notes below); the binding remains available with `-o vapoursynth/*:python_module=True`.
- When the binding is enabled, install or reuse `Cython >= 3.1` through an interpreter that can actually run `python -m cython` (the recipe verifies the wrapper by transpiling a probe module during `generate()`), inject a Conan Meson native-file `cython` wrapper, and build the OHOS Python extension by probing real libpython candidates from `sysconfig`, the Python executable prefix, and OHOS runner locations before adding `link_args`.
- Patch Meson so disabling the Python-related options still skips unconditional Python/Cython probing when `python_module=False`.
- Provide a non-empty C consumer test that links against `libvapoursynth`, checks `getVapourSynthAPI`, verifies API version, and creates/frees a `VSCore`.
- Cap the Meson compile fan-out (`tools.build:jobs` when the profile sets it, otherwise `min(8, cpu_count)`): the CI workers run under a sandboxed uid with a tight process budget, and Conan's default of one job per CPU (20 there) makes ninja abort with `ninja: fatal: posix_spawn: Resource temporarily unavailable`. Other recipes in this repository apply the same kind of cap.
- Package upstream Python tests plus the upstream expression debugger source. `test_package` compiles an OHOS `ExprDebugger.exe` and always runs `expr_compiler/compiler_test.py` through it; with the binding enabled it also runs the 11 upstream unittest modules (live import on a device, static module verification when the sandbox reports E212).

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

- `zimg/3.0.6` is published in `ohpcd` and resolved by the official CI (L0i reports the dependency in the registry).
- The Python binding cannot be produced on the CI worker: Cython ships compiled modules such as `Cython/Utils.cpython-312-*.so`, and hmmac refuses to dlopen anything from a user path (`~/.local`, the Conan cache on `/storage/Users`) inside an `hnp_file`-context python3 (CI #92986: `ImportError: Error loading shared library .../Cython/Utils...so: Permission denied`, `knowledge/doc/E212.md`). The same rule blocks importing the built extension. The recipe therefore defaults to `python_module=False`; enabling it on such a worker fails with an explicit E212 explanation instead of a cryptic Meson error.
- The Meson `cython` wrapper must exec an interpreter that can really run Cython: CI #92945 reported `ERROR: Compiler /system/bin/sh .../cython-wrapper/cython cannot transpile programs` because the wrapper used a bare `python3` from the Meson check environment. The recipe now enumerates the python3 candidates, verifies each with `python -m cython --version`, and probes the generated wrapper with a real `.pyx` during `generate()`.
- OHOS signing tools differ per machine: developer devices expose `/storage/Users/currentUser/usr/local/bin/{llvm-objcopy,binary-sign-tool}` while the CI workers only expose `/data/service/hnp/bin/*`. The recipe enumerates candidates (environment variables, usr-local, PATH, compiler directory, hnp, OHOS SDK) and signs with the first executable one instead of a hard-coded path.

## True-device validation

- Device job: `/storage/Users/currentUser/ohos-users/codex-vapoursynth/vapoursynth-74-20260728-r1`
- Command: `sh "$HOME/ohos-users/codex-vapoursynth/vapoursynth-74-20260728-r1/run-conan-heavy.sh"`; the optional binding is validated with the profile that appends `[options] vapoursynth/*:python_module=True` (see `run-conan-module.sh` in the same job directory).
- **Default path** (`python_module=False`, this is what CI builds): `/storage/Users/currentUser/ohos-test-runs/codex-vapoursynth-74-vapoursynth-74-20260728-r1-conan-20261015-173546-64022` — exit code 0, `options: python_module=False`, `Meson compile job fan-out capped at -j8`, `vapoursynth core API smoke test passed`, `expr_compiler compiler_test.py passed: 69 expressions`, `L0/L1/L2/L4/L5 = pass/pass/skip/pass/pass`.
- **Binding path** (`-o vapoursynth/*:python_module=True`): `/storage/Users/currentUser/ohos-test-runs/codex-vapoursynth-74-module-vapoursynth-74-20260728-r1-module-conan-20261015-173737-4027` — exit code 0, `vapoursynth python import probe passed`, `Ran 157 tests in 91.137s` → `OK`, `expr_compiler compiler_test.py passed: 69 expressions`, `L0/L1/L2/L4/L5 = pass/pass/skip/pass/pass`, `Success: 1`, `Failed: 0`.
- Cython evidence from the binding run: `Cython 3.3 available via /storage/Users/currentUser/usr/local/bin/python3`, `Cython wrapper probe: transpiled a probe module successfully`, `Cython compiler for the host machine: /system/bin/sh .../cython-wrapper/cython (cython 3.3.0)`.
- Both runs used `conanfile.py` sha256 `40154f6100393c5a7925d4e1126b65a25858758afadba724a81639892224f666`, i.e. the revision merged here.

Earlier runs kept for history: `...-conan-20261015-152702-62492` (Cython 3.3.0, module enabled by the then-default), `...-conan-20261015-154235-10367`, `...-conan-20261015-155937-22217` and `...-module-conan-20261015-160239-27229`.
