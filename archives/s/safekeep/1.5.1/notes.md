# safekeep 1.5.1 Build Notes

Date: 2026-07-31

## Summary

SafeKeep 1.5.1 is a Python 3 command-line backup manager. The Conan recipe
packages the upstream `safekeep` script as `bin/safekeep` and includes the
upstream `safekeep-test` integration test driver, configuration sample, cron
script, text documentation, and sample backup file under `share/safekeep`.

The SourceForge release links listed by upstream returned HTTP 403 in this build
environment. The recipe therefore uses the GitHub `1.5.1` tag tarball from
codeload, which downloaded successfully with SHA-256:

`c5efcbbdb8e141d6aeac648c4833f935f5982c01f58cd26ff6b35fcc43c609fb`

For CI environments with restricted outbound access, the same verified archive
is exported with the recipe as `safekeep-1.5.1.tar.gz`. The `source()` step uses
that local archive first and falls back to the upstream codeload URL only when
the exported archive is unavailable.

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

The OHOS runner used here does not provide `rdiff-backup` or the mutable
client/server environment needed for the upstream integration flow. The Conan
`test_package` packages `safekeep-test` and verifies its local/remote test
markers, while still checking the installed CLI, config, docs, and sample backup
definition.

## OpenHarmony Validation

- run dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-1.5.1-safekeep-1.5.1-upstreamtests-r1-conan-20260731-212720-26678`
- full ref: `safekeep/1.5.1#42db37736a941feadbc70de01083dccc:fc3eeb021243959114a0318489539cad6d087e28#6ae8de352ed3d8f2b5bea74d1ebb40f4`
- gates: `L0=pass`, `L1=pass(test_package executed)`, `L1e=pass`, `L2=pass(safekeep --version OK)`, `L4=pass(no patches)`, `L5=pass(bin/ has content)`.
