# DRAFT: GNU Mailutils on HarmonyOS — HMDFS owner mapping, hardlink denial, and missing passwd records

- **Trigger instance**: mailutils 3.20, HarmonyOS PC device, PR #15271
- **Category**: filesystem | HMDFS | libc | account lookup | upstream tests
- **Phase**: runtime and testing
- **Status**: evidence-backed draft for this adaptation

## Symptoms

Three independent platform behaviors surfaced in the upstream Autotest suites:

1. File Safety cases reported `File owner mismatch` for files created by the test process. In the captured device run, `getuid()` was `20020085` while `stat().st_uid` for a newly created HMDFS file was `20001006`.
2. HMDFS rejected hardlink operations with `EPERM`. Maildir append/flag transitions that use `linkat()` consequently failed even though the source and destination directories were writable.
3. The device's application UID had no passwd database record. `getpwuid()`/`getpwnam()` could return `NULL`; comsat's test path then failed when it treated a missing `struct passwd` as a valid pointer.

These are separate conditions. A mapped file owner does not imply an invalid account lookup, and lack of a passwd record does not imply that hardlinks are unavailable.

## Root cause and evidence

HMDFS presents file-owner metadata through a mapped UID that may differ from the process UID. Code and tests that require `st_uid == getuid()` therefore encode a POSIX local-filesystem assumption that does not hold on this mounted filesystem. The device also rejects hardlinks on HMDFS, so a successful `link(2)` cannot be assumed from directory writability alone.

HarmonyOS application UIDs may have no entry in the traditional passwd database. POSIX account lookup APIs can legitimately return `NULL`; callers must check the result before dereferencing it. An environment name such as `LOGNAME` or `USER` can identify the current test process, but it is not a replacement for arbitrary system account lookup.

The earlier on-device `make -k check` run recorded nine File Safety failures and six comsat failures among 1,389 executed cases. The corresponding failures were retained in suite logs; they were not converted to skips.

## Adaptation pattern

- For a test helper comparing file safety behavior, `stat()` the test file and pass its reported owner into the check when HMDFS reports a mapped UID. Keep the production `mu_file_safety_check()` policy intact; do not rewrite file owners or skip the case. A consumer assertion still rejects an explicit foreign UID.
- For comsat test mode, do not dereference a missing passwd record. Accept a non-root `.biffrc` owner in test mode when HMDFS maps the owner; production mode still requires the passwd uid.
- For Maildir's temporary-file transition, attempt `linkat()` first. Use `renameat()` only when the filesystem reports a known unsupported-link error (`EPERM`, `EACCES`, `EOPNOTSUPP`, or `ENOSYS`); preserve other failures. Rename is appropriate here because the temporary and destination entries are on the same filesystem.
- For identity lookup, check all `getpwuid()`/`getpwnam()` results. A fallback to `LOGNAME`/`USER` is limited to the current process identity. Keep comsat's user-switch bypass confined to test mode, and guard its optional `.biffrc` lookup when no passwd record exists.
- In tests that specifically exercise hardlink behavior, use a clearly identified fixture fallback only when hardlink creation fails; do not treat all filesystem errors as success.

## Boundaries

This pattern makes current-user tools and upstream tests usable when the device has no passwd record and HMDFS maps ownership. It does not create a real login record, grant privileges, or establish that an arbitrary file is safe. Production account and ownership policy must still use the metadata and identity model exposed by the target platform.

## Existing knowledge and added scope

The formal knowledge base already records the individual platform behaviors: E011 describes HMDFS UID mapping in temporary directories; E079 describes HMDFS hardlink denial; E338 describes a missing passwd entry causing a null dereference in an application home-directory path. This draft does not claim those behaviors are new. The reusable case here is their combined effect in a mail stack: a file safety test can compare two valid but different owner identities, Maildir's link-based commit can fail, and a daemon's test-mode account lookup can return null. The adaptation keeps production file safety intact and scopes the identity fallback to the current user and the comsat test path.

## Related implementation

- `archives/m/mailutils/3.20/patches/0012-mailtools-current-user-fallback.patch`
- `archives/m/mailutils/3.20/patches/0013-maildir-linkat-rename-fallback.patch`
- `archives/m/mailutils/3.20/patches/0014-testsuite-fsaf-hardlink-fallback.patch`
- `archives/m/mailutils/3.20/patches/0016-testsuite-fsaf-hmdfs-owner-mapping.patch`
- `archives/m/mailutils/3.20/patches/0017-comsat-test-mode-user-bypass.patch`
- `archives/m/mailutils/3.20/patches/0018-testsuite-fsaf-hmdfs-owner-check.patch`
- `archives/m/mailutils/3.20/patches/0019-comsat-test-mode-passwd-guard.patch`
