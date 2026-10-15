# indi-pentax 1.0 native test report

Official OHOS profile on aarch64 HarmonyOS PC; Conan create compiled, linked,
installed both executables and ran the installed CLI consumer: 10 discovered,
10 executed, 10 passed, 0 failed/skipped. See conan-create.log and the
HMBS_TEST_PACKAGE_RESULT line. The pinned upstream subproject has no automated
test suite (0 tests, ratio N/A). No physical camera is available; capture,
device permissions, exposure and real image transfer remain pending. Ricoh
PTP is excluded by the original upstream aarch64 build.

Tests: color/gray JPEG FITS pixels, DNG RAW pixels/Bayer metadata, missing JPEG,
invalid RAW/JPEG, JPEG error after header, output preservation, invalid args,
and INDI MSC empty enumeration/EOF contract. CLI tools expose no library API.

W3 local CI ran the unmodified official setup.sh and build_and_test.sh on
2026-10-02 and passed. L0/L1/L2/L5 passed; L4 warned about legacy function
names in patches. Driver --version/--help is unsupported by INDI's process
entry; the XML/EOF test exercises its actual public interface. A separate
readelf audit verified both shipped executables are AArch64 PIE with NX stack,
RELRO and BIND_NOW. The installed bundle was relocated outside Conan and
passed the same 10 cases with only bundle/lib in LD_LIBRARY_PATH.

The raw W3 log SHA256 is
`72742fa50b0fe0618aa189b98a7f89f2d97b94ebeb4596886eff9be69fa3b832`.
The .ci-result.json is copied unchanged from the real finish tool output;
it is local state, excluded from submission. Raw logs and the 20-file bundle
are in the external delivery directory output/indi-pentax-1.0.

ConanVerifier's G4/L2/L4/L5 were internally skipped because its old cache-ID
parser did not resolve the Conan 2 result. They are not counted as executions.
Actual artifact/runtime/hardening evidence comes from W3 and the explicit
package relocation/ELF checks. The legacy clean-verify helper expects an
Autotools ./configure tree, so its result is not a CMake clean-build result;
the real Conan source download, hash validation and patch replay succeeded.

Overall finish exited 1 after W3 due archive/knowledge readiness warnings,
including existing E219/E253/E305 fields and the legacy packaging markers.
graph validate itself passed (542 KV/MD pairs). This report does not claim
all finish stages or official remote CI passed.

## 2026-10-14: text-only fixture transport

CI checkout-pr used a web diff without binary payloads. Store the same three
JPEG/DNG fixtures as Base64 text and restore them in the consumer temporary
directory, verifying pinned SHA256 before invoking the installed programs.
All three decoded fixtures match the original Git blobs byte-for-byte.
Malformed Base64 and a wrong decoded checksum both fail before CLI execution.
Native OHOS `conan test` against the existing validated recipe revision
`a2bb7861c99ca8654d1886bfbe119779` passed 10/10, 0 failed/skipped (p046.log).
The full PR text diff applies to an empty isolated Git repository without
binary patch data; no product source, test cases or pixel assertions changed.

The updated consumer also passed the official local CI simulation (p048):
JC/L0/L1/L5 pass, 10/10 consumer tests; L2 CLI version/help checks skipped
(standalone probes returned nonzero; cause unresolved, while the installed
CLI consumer passed in conanrun), L4 retains legacy function warnings. The raw
log is w3-fixture-fix-20261014.log; overall local CI exit code is 0.
