# CI92608 — permission fixture filesystem repair

## Actual failure

PR15756, failed HEAD e17863811e36d7b3c6efe5ca0de80f7e2469368d.
Build92608/buildid106531, CI-011. Source download, all15 patches and compilation
completed. CTest ran37 cases:36 passed; dispatch_io failed at the asynchronous
write-to-protected-directory assertion: actual0, expectedEACCES(13).
This is not the earlier PATCHES namespace collision or worker fork exhaustion.

## Repair and preserved coverage

For OHOS, Conan preserves the native absolute TMPDIR in
DISPATCH_TEST_PERMISSION_TMPDIR before assigning ordinary test scratch to its
build folder. Only the private mkdtemp permission fixture uses this native
filesystem. After chmod(0), synchronous exclusive create/open must fail with
EACCES before exercising asynchronous dispatch_io error propagation.
An unexpectedly successful probe is closed/unlinked and the test fails.

The original asynchronous EACCES assertion,256-byte unwritten-data assertion,
successful channel-to-channel write and10240-byte readback remain unchanged.
All37 CTest IDs remain registered, no skips or changed expected errno.
The original15 automatically generated per-file patches retain their names;
only dispatch_io.c changes. No production scheduler/ARM64 implementation changes.

## Verification

Fresh native Conan transaction libdispatch-conan-w3-20261014-r8 is the
authoritative shared/static repair verification. Its terminal result and exact
artifact hashes were independently collected after all12 transaction phases
passed and the runner exited. Earlier native PASS and platform AI Review are
historical, not this repair's result.
User-authorized alternate endpoint10.62.201.39:2222,
bootbd99f7a0-d41d-46ac-a8f8-bc089feaf6dc,
UID20020084. Official source SHA256
68ac837bc127ab2ca96c24bbf2fd58ebc737a8ef43656c211667540fcda62ce6.

The previous machine's r5 passed shared37/37+consumer1/1 but failed static
linking because its shell could not fork; aggregate FAIL is preserved and is
not combined with results from this device. Alternate-device r7 exposed a
local clang shell wrapper injecting -Wl,--code-sign into compile-only commands,
which upstream -Werror correctly rejected. r8 uses the actual published
clang-15 and matching sysroot in a task-private Conan profile, C++ driver mode,
and linker-only flags in linker configuration; no global compiler wrapper is
edited and no warning is suppressed. The recipe signs its own output ELFs.
The profile and source/recipe bytes are frozen in this transaction's bundle.

| Mode | Registered/executed/passed upstream | Packaged consumer | Result |
| --- | --- | --- | --- |
| shared | 37/37/37 | 1/1 | PASS |
| static | 37/37/37 | 1/1 | PASS |

Both dispatch_io JUnit outputs explicitly record synchronous kernel probe
Actual13/Expected13 PASS, asynchronous protected-directory write
Actual13/Expected13 PASS, and unwritten dataActual256/Expected256 PASS.
This verifies the missing fixture precondition and original failure oracle,
not merely a successful test exit. No skipped/error/failure JUnit elements;
both actual ID sets match their37-item CTest inventory.

Formal log SHA256:
3b537ce0c62a034c466d6d34d99d027705ee6ca645f5a8206f969d7221599ea5.
Shared JUnit SHA256:
38e84079cb1903c20dbb2422bed9f98c877906be6a89f3dcafee8469a50202e6.
Static JUnit SHA256:
1cbc14aefacd3ba5f21e53be1ba595e90249b3e320e96f91367130e6c47d0db1.
Recipe RREV efe40146ea94903e472a711911fefbdd;
shared PID01d92cf349a0dd98ff915f4bd99a04430171517f,
PREVd1eb65b8cde249e2ef17afabb8ec1116;
static PID21b17f8b2bc0e9511e276e3d57a23893067cefe5,
PREVd831a44880dcf6106f64b0b962ac1d09.

Independent official finish libdispatch-finish-w3-20261014-r7 also completed
with actual RC0. Its ConanVerifier and local CI each separately ran37/37
upstream tests and consumer1/1. G1-G4, L4/L5, W5 and W2 passed; all12 receipts,
release/postrelease passed and owned runner/children exited. The legacy
optional G0 clean-verify reported missing its historical tarball location;
both actual Conan clean-source executions passed, so this nonblocking warning
is not represented as a separate G0 clean-verify PASS.

Finish aggregate SHA256:
724f358cc991e4f3e68b2a9bd7696049079be6647e56a501b8bc53a4c202449f.
Actual local-CI log SHA256:
1e83328da23e28d0c4d91a900dbe19657886663b204a7892f565c287088b914f.
Producer CI result exit0, integrity9419e148a4d95bf6; actual timestamp/log hash
independently recomputed, copied byte-for-byte, never hand-created/edited.
Runtime recipe/test/patch hashes match both frozen runs. Final metadata edits
do not change those runtime inputs. No result is assembled across devices.

## Classification and boundaries

This is a test-filesystem portability repair using standard environment
plumbing and POSIX APIs. HD1private OS integration, HD2private toolchain,
HD3complex architecture implementation and HD4massive dependency/test cost
remain supported negatives; pathA+B, notC. One published musl-fts test-only
dependency; unchanged tractable37-case suite and installed API consumer.
Knowledge increment E551-draft-LD66 extends E046/E223 with a no-skip negative
permission fixture and the TMPDIR override boundary.

If the selected native temporary filesystem also ignores DAC, this repair
fails explicitly. It does not grant permissions, modify system mounts, accept
errno0, skip the test or claim worker CI/merge/publication success.
