# oRTP native test report — 2026-10-15

Environment: HarmonyOS 6.1.0.117 arm64, OHOS Conan 2.29.1 / Clang 15,
Release shared build, native host/build profile, two jobs.

| Scope | Total | Passed | Failed | Skipped |
|---|---:|---:|---:|---:|
| Complete original upstream ortp_tester (FEC/first) | 1 | 1 | 0 | 0 |
| Strict installed consumer | 1 | 1 | 0 | 0 |

The original FEC test asserts a NULL pointer only. It is a placeholder framework
test, not algorithm coverage. No test source or assertion was modified. Network
send/receive tools stay disabled and are not counted. Consumer actually ran
init, scheduler/session configuration, loopback bind and destroy; failures propagate.

Official infrastructure ref: b544378a4ea82b4959135eebb21f5e509eeebf91.
Actual FinishPipeline.step35_local_ci exit 0, marker hash matches original log.
G0/KC/JC/L0/L1/L4/L5 pass; L2 skip (no delivered CLI).
Destructive negative package-dependency test passed; not counted as another upstream case.

W3 log SHA256: `2d92a85b0878b89dd531527e94a4ee891ffbd2cb6a735571498d6425b57ada2a`.
Positive Conan create SHA256: `18ff954a0b87515cf39f6f293cacf474654bb1ee6d0cc433c16b098c0d1b1af0`.
Raw evidence: `.tmp/pr-monitor/ortp-w3-evidence/evidence/` and
`pipeline_logs/ortp-w3-final-v4-20261015-device.log` in the maintenance workspace.
Three failed attempts remain recorded separately (patch ordering, CMake includes,
own build DSO path); the final complete rerun used the corrected candidate.

At the initial native run, remote CI and publication awaited separate verification.
The CI95092 follow-up below supersedes the remote-CI pending state only.
Prior CI #92908 tested 90261cae and ran consumer only. Static builds, real RTP
interoperability and FEC algorithms are outside this evidence.

## Remote CI follow-up — 2026-10-16

[CI95092](https://ohpcd.atomgit.com/ci?id=95092), Buildbot109411 / CI-028,
completed successfully (exit 0). Requested revision:
`1fb7f327d385ecf6b7eed77604810b426827dcec`, containing source fix
`fb71955932916f66582fcb0a73773d42e8319f8d`.

| Actually executed scope | Passed | Failed | Skipped |
|---|---:|---:|---:|
| Original upstream ortp_tester / FEC/first | 1 | 0 | 0 |
| Installed API consumer | 1 | 0 | 0 |

The destructive negative package-dependency check passed separately.
L0/L1/L4/L5 passed; L2 CLI smoke check skipped. Conan's skipped bcunit binary
is not a skipped test. The original FEC placeholder remains a placeholder.

Raw log in the maintenance workspace:
`pipeline_logs/pr15662-conan-build-test-20261016-build95092-full.log`.
SHA256: `52e5d7954784d9be477e1ce116c9b060b1d4118c1421cfd4904a8804f9449af1`.

Buildbot ci_revision identifies the requested revision; its live PR diff
checkout has no full source-content digest. Publication remains unverified.
This documentation update did not rerun local code tests or transfer CI95092's
result to a later documentation head.
