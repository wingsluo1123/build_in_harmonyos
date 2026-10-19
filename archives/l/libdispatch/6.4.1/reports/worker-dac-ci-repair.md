# CI93083: capability-based permission fixture selection

The complete raw CI93083 log is bound to PR15756 HEAD
a10e2171b676cd6ec5b1be3d3a7adcbe8bb247c8 and CI-021.
SHA256:5530fcaee20c44436e2e6278a78a0b4297f529459d77a3aec2110181ee608149.
Compilation succeeded, but dispatch_io's kernel permission precondition returned
0 rather than EACCES13:36/37 tests passed. This is a real fixture failure,
not the earlier worker fork exhaustion or the nonfatal curl predownload warning.

Saving the original worker TMPDIR was insufficient: that location can also
be on a filesystem which accepts chmod without enforcing directory DAC.
The recipe now tries the original absolute TMPDIR and sandbox temp/cache
candidates. Each unique owned mkdtemp fixture must deny exclusive creation
with EACCES after chmod000, and permit creation after restoring0700.
The fixture is then cleaned. No existing parent is chmodded or removed.
Only a capability-proven root is passed to the unchanged C test, which repeats
its own kernel check before the original asynchronous EACCES and256-byte
unwritten-data oracles. All candidates failing is a hard build failure.

All37 registered test IDs and public consumer assertions are unchanged.
The original permission-test source patch0008 is unchanged. Windows bounded selector checks2/2 use a mock
and are not native permission evidence. E551-draft-LD66 is extended rather
than creating a duplicate chmod knowledge entry.

The new210132 Conan r10 transaction remains FAIL: shared completed37/37 plus
consumer1/1, static passed dispatch_io but dispatch_concur observed peak9
instead of10 during concurrent same-device validation. It was released and
collected with its real failure. No assertion was relaxed, no test skipped,
and no part of that failed transaction is promoted into a complete PASS.

Released r11 on20139 also remains FAIL: dispatch_read2 received315 callbacks
instead of320, although the complete10240 bytes arrived. Its kernel EACCES
fixture passed. Independent historical finish r8 passed37/37 twice, but it
predates the following timing-fixture source corrections and is not reused.

Two fixture postimages are now corrected and regenerated with the official
refresh-patch generator:0005 uses a30-second bounded semaphore rendezvous to
establish actual submission overlap before callbacks finish;0011 acknowledges
each32-byte delivery before the next pipe write. The original peak-width,
workload,320-delivery and10240-byte assertions remain. No retry loops, sleeps
extended to conceal failures, expected-count reductions or test exclusions.
The two generated patches pass GNU patch dry runs against pristine source;
the other13 patches remain byte-identical. New native results must bind this
successor, not either earlier failure or the pre-timing-fix finish.

## Current formal native verification

libdispatch-conan-w3-20261014-r12 on210132:2222, boot
12b3ceb3-5bf3-49a1-bb4d-00508715a64f, UID20020084 completed shared/static
serially. Each mode passed the exact37 registered upstream IDs and installed
public consumer1/1, with no failed/error/skipped JUnit cases. The real
permission-case stdout independently proves synchronous EACCES13, asynchronous
EACCES13 and256 unwritten bytes in both modes. The corrected concurrency and
320-delivery cases passed without reducing their original assertions.

Formal log SHA256:
7b6fb4238a0b7837a97c29a78df3f8f868afb230c6da45fc704f67b8742e3cb1.
All12 immutable receipts PASS/NOT_REQUIRED; one launch, runner and owned
children exited, release/postrelease PASS, exact-byte artifacts collected.
Two linkage modes repeat the same37-test inventory; they are not74 independent
tests. The source remains the official SHA256-bound Swift6.4.1 release.

## Independent official finish and local CI

libdispatch-finish-w3-20261014-r9 on20139:2222, boot
bd99f7a0-d41d-46ac-a8f8-bc089feaf6dc, UID20020084 completed the actual official
finish command with RC0. ConanVerifier and the independent local CI each
passed37/37 upstream tests and public consumer1/1. G1-G4, L4/L5, W2/W5 and
12-phase release/postrelease passed. The optional legacy clean-verify lookup
did not find its historical tarball location; this warning is not called a
PASS and did not replace the two real Conan clean-source executions.

Aggregate finish SHA256:
0fb6b46407c5a4ec267ff323baea2ab807252540826ce45ccedde89bd0ebb3f7.
Independent local CI log SHA256:
ca77b45ea4d104c3abd04ad392d08ae67779e260c2819890b6026949380cab4f.
The actual producer result timestamp is2026-10-15T23:59:32.840224,
exit_code0, integrity a9a67c8c6636c71e. Its bytes and log hash were verified
and copied unchanged; no CI marker was authored or edited. Runtime recipe,
patch and consumer hashes match both complete new transactions; metadata-only
report updates do not reuse an old runtime proof.

These are native validation/local CI results, not competition-worker CI,
platform Review approval, merge or publication. The pre-timing-fix finish r8
and failed Conan r10/r11 stay separate immutable historical attempts. Task
private profiles and framework projection are not part of the software PR.
