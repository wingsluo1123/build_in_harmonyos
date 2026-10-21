# utm 0.8.1

Upstream is the Python coordinate conversion library at https://github.com/Turbo87/utm,
not the unrelated UTM virtual machine application. The source release requires Python
3.8 or newer; this recipe requires Python 3.9 or newer for the pinned pytest runner.

The package has no required third-party runtime dependency. NumPy is optional and is
not bundled. In a Python installation without NumPy, the unmodified upstream suite
collects 164 tests, passes 132 and skips its 32 vector-operation tests using upstream
skipif conditions. No test file or skip condition is changed.

The build runs the whole upstream test directory and writes upstream-tests.xml.
pytest and its dependencies are pinned with SHA256 checks and used only for testing.
The package installs the utm modules, distribution metadata, license, upstream CLI
and a launcher. The launcher resolves the package relative to itself and uses the
real native Python interpreter path, without retaining the build virtualenv path.
It adds --version and otherwise delegates to the original upstream CLI.

VirtualRunEnv provides PYTHONPATH and the command directory. test_package executes
six unittest cases against the installed package, including both CLI directions
and rejection of non-numeric coordinates, out-of-range latitude and invalid zones.
The CLI tests also clear PYTHONPATH to verify its relative module lookup.

On OHOS, test_package also executes one HarmonyOS-only storage relocation case.
It checks the native HarmonyOS aarch64 kernel and runs the copied CLI from a Chinese
path containing spaces in writable device storage. Both Python path overrides are
removed and forward/inverse results are checked. The Linux profile does not execute
this platform test. See the PR for validation results tied to the current commit.

```sh
conan create archives/u/utm/0.8.1 --build='utm/*'
CI_PACKAGES=archives/u/utm/0.8.1 CI_BRANCH=feat/utm-0.8.1 zsh ci/conan/build_and_test.sh
```
