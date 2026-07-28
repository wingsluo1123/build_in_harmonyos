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

Optional or deferred:

- Python >= 3.12 for VSScript and Python module.
- Cython for the Python module.

Local/remote status:

- `zimg/3.0.6` was merged to `origin/main` by `e4d4a930a31fbd8eeeefd1ad14345fe64fc4a3a7` (`【依赖项】feat(zimg) 3.0.6`) and is associated with issue #1459.
- `conan download "zimg/3.0.6" -r=ohpcd --only-recipe` still fails on this workstation with remote policy error: `system acceleration policy not enabled`.
- `conan list "zimg/3.0.6:*" -r=ohpcd` also returns `system acceleration policy not enabled` here, so ohpcd binary publication cannot be confirmed from this host.
- After rebasing this branch to latest `origin/main` and exporting `archives/z/zimg/3.0.6` as `zimg/3.0.6`, `conan install` resolves the zimg recipe from local cache.
- The same `conan install ... --build=never` then stops at the expected missing binary for OHOS/armv8: `Missing binary: zimg/3.0.6:01d92cf349a0dd98ff915f4bd99a04430171517f`.
- `conan download "python/3.12.9" -r=ohpcd --only-recipe` failed with the same remote policy error.
- `conan list "python/3.12.9" -r=ohpcd` reported `Recipe 'python/3.12.9' not found`.
Conclusion: the old missing-recipe blocker is cleared in git. Final VapourSynth CI now depends on the runner being able to build or fetch the `zimg/3.0.6` OHOS binary. Python/Cython should be handled separately if the package is expected to ship the Python module used by plugin runtime tests.

## Source/build-system analysis

- Build system: Meson. Upstream declares `c`, `cpp`, and `cython`; this recipe patches Meson so Cython is only required when the Python module is enabled.
- Default upstream options build core and VSScript, while `vspipe` and the Python module are force-disabled unless `build_wheel=true`.
- Core library builds `libvapoursynth` and installs public headers plus `vapoursynth.pc` when `build_wheel=false`.
- Core links `zimg` statically through Meson dependency lookup and also uses threads and `dl` on non-Windows platforms.
- Upstream test directory contains Python tests for the Python module/runtime; they are not run in this precheck recipe.

## Recipe strategy

- Use MesonToolchain + PkgConfigDeps.
- Require `zimg/3.0.6` explicitly; do not use Meson wraps or vendored fallback.
- Disable x86 asm for HarmonyOS/armv8.
- Disable VSScript, vspipe, and Python module by default to avoid introducing unprepared Python/Cython dependencies in this PR.
- Patch Meson so disabling VSScript/Python module also skips unconditional Python and Cython dependency probing.
- Provide a non-empty C consumer test that links against `libvapoursynth`, checks `getVapourSynthAPI`, verifies API version, and creates/frees a `VSCore`.

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

- `zimg/3.0.6` recipe is merged, but ohpcd binary availability could not be confirmed from this workstation. The true-device isolated validation exported the merged local zimg recipe and reused the locally built OHOS package.
- Python module is intentionally disabled in this first precheck recipe. If downstream tests require `import vapoursynth`, plan a follow-up within the VapourSynth PR after Python/Cython dependencies are confirmed, not in the `mvtools` PR.

## True-device validation

- Device job: `/storage/Users/currentUser/ohos-users/codex-vapoursynth/vapoursynth-74-20260728-r1`
- Latest passed run: `/storage/Users/currentUser/ohos-test-runs/codex-vapoursynth-74-vapoursynth-74-20260728-r1-conan-20260728-233538-34842`
- Command: `sh "$HOME/ohos-users/codex-vapoursynth/vapoursynth-74-20260728-r1/run-conan-heavy.sh"`
- Result: pass. `vapoursynth/74` built, packaged `libvapoursynth.so.4`, copied `libvapoursynth.so` for consumers on non-symlink platforms, executed the direct C smoke test, and passed the destructive negative test.
- Summary: `L0_RESULT=pass`, `L1_RESULT=pass`, `L2_RESULT=skip` (no `bin/`), `L4_RESULT=pass`, `L5_RESULT=pass`, `Success: 1`, `Failed: 0`.
