# safekeep 1.5.1 Build Notes

Date: 2026-08-01

## Summary

SafeKeep 1.5.1 is a Python 3 command-line backup manager. The Conan recipe
packages the upstream `safekeep` script as `bin/safekeep` and includes the
upstream `safekeep-test` integration test driver, configuration sample, cron
script, text documentation, and sample backup file under `share/safekeep`.

The SourceForge release links listed by upstream returned HTTP 403 in this build
environment. The recipe therefore uses the GitHub `1.5.1` tag tarball from
codeload, which downloaded successfully with SHA-256:

`c5efcbbdb8e141d6aeac648c4833f935f5982c01f58cd26ff6b35fcc43c609fb`

For restricted CI networks, the same verified archive is committed beside the
recipe as base64 text in `safekeep-1.5.1.tar.gz.b64` and exported through
`exports_sources`. The `source()` step decodes it back to
`safekeep-1.5.1.tar.gz`, validates the decoded archive with the same SHA-256,
and unpacks it before falling back to the upstream codeload URL. The text form
also keeps the PR diff applyable on CI workers that fetch merge requests as
plain `.diff` files that do not carry binary payload data.

## Runtime Notes

The script imports Unix-only modules such as `pwd` and `fcntl`, and it shells out
to system backup tools. The Windows-local test package intentionally avoids
executing the command and verifies the packaged command, version marker, docs,
sample config, and sample backup definition instead.

Runtime use on OpenHarmony requires Python 3 plus external tools such as
`rdiff-backup` and OpenSSH. Snapshot and database backup modes may require
additional utilities.

The upstream command script uses an absolute Python shebang. During packaging it
is rewritten to `#!/usr/bin/env python3` so the OpenHarmony runtime uses the
available Python wrapper from `PATH`.

## Upstream Tests

Upstream provides `safekeep-test`, a Python integration test driver with local
and remote backup modes. The local path creates a temporary backup tree, runs
`safekeep --server`, restores with `rdiff-backup -r now`, and compares MD5
sums. The remote path additionally assumes SSH access, root setup, package
deployment, and target host mutation.

For OHOS, the recipe applies a test-only patch to `safekeep-test` and the Conan
`test_package` runs the upstream local flow as
`SAFEKEEP_TEST_OHOS_LOCAL=1 safekeep-test --local --reps=1`. The patch keeps the
upstream driver structure and changes only the local test harness needed by the
runner:

- uses a local safekeep client emulator for the server/client protocol;
- launches the server from the wrapper directory so OHOS Python subprocess can
  resolve `safekeep --client` without relying on PATH lookup;
- disables the default `nice`/`ionice` adjustments that are unavailable in the
  runner;
- keeps the repository under the test temp root and restores through
  `rdiff-backup restore --at now` with a relative repository path, avoiding
  OHOS parent-directory permission checks under `/storage/Users`.
- relocates the `rdiff-backup/2.2.6` package tree into the test `TMPDIR`,
  prepends that copy to `PATH` and `PYTHONPATH`, and marks copied Python
  extension modules executable. This avoids OHOS HNP Python rejecting `dlopen`
  from Conan package-cache paths while still running the real `rdiff-backup`
  entry point and Python modules.

The OHOS upstream local flow now passes. The remote flow is still identified but
not executed because it requires SSH, root setup, package deployment, and
mutable client/server hosts. The actual upstream integration result for the
release driver is therefore `1/2`: local passed, remote not run.

## OpenHarmony Validation

- run dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-safekeep-safekeep-1.5.1-upstream-local-patched-r5-conan-20260801-172459-7540`
- full ref: `safekeep/1.5.1#d898cdcabe2463356b45068f5c3fdfad:fc3eeb021243959114a0318489539cad6d087e28#038652399e5f3c35c9df42c31b2d5451`
- gates: `L0=pass`, `L1=pass(test_package executed)`, `L2=pass(safekeep --version OK)`, `L4=pass(test patch clean)`, `L5=pass(bin/ has content)`.
- upstream local execution: `SAFEKEEP_TEST_OHOS_LOCAL=1 safekeep-test --local --reps=1`, result `1/1 passed`.
- upstream integration result: `1/2`; local flow passed on OHOS, remote flow was
  not executed for the SSH/root/mutable-host reasons above.
