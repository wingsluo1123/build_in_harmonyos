# Native libplist 2.8.0 verification

Device: allowed endpoint 10.62.201.39:2222, OHOS ARM64, Clang 15, libc++, Conan
2.29.1. Boot identity bd99f7a0-d41d-46ac-a8f8-bc089feaf6dc; UID 20020084.
Run libplist-conan-w3-20261015-r2; original upstream tar/SHA-256, private cache,
independent fresh transfer/readback and a single native launch.

| Category | Result per link mode |
|---|---:|
| Complete original Automake test suite | 43/43 PASS |
| Installed C API binary roundtrip | 1/1 PASS |
| Installed OHOS plistutil JSON→binary→XML→JSON workflow | 1/1 PASS |

Both shared and static builds passed. There were zero skips, XFAILs, failures or
errors. Total upstream denominator remains 43, not 86. Added consumers are two
cases; the Harmony-specific workflow is one of them, not an extra third case.

The frozen native validator accepted the full twelve-phase receipt chain,
including release/postrelease and no retained task process. Full Conan log
SHA-256: `1996d1cb59884369fd364210edb965afcd3dda29096bc681ea04ff600307f132`.
Exact collected logs, graphs and receipt proof are in the task-owned
libplist-conan-w3-20261015-r2/collected directory.

Official skill finish also ran in libplist-finish-w3-20261015-r4: conan-verify
and the real W3 CI substep passed. The frozen validator accepted the complete
twelve-phase chain, release and zero retained task processes. Full collected
log SHA-256: `5fd99f884ec37332d476da6555c435c1a6cc3dcfaf16959bc72b2ebd70e03c08`.
Its original generated CI result binds W3 log SHA-256
`eadafc4b2362cd343a2b2dd58b060e09bde6ddad6000baa669fe1e8f886cc20d`.
The aggregate finish is PARTIAL_POST_W3 due to shared pre-existing graph
warnings (step5b/step8); candidate knowledge has its separate Pre-PR gate.
Old failed wrappers remain FAIL. Platform Review/CI and publication are not
claimed by this native result.
