# Native libxls 1.6.4 verification

Device: allowed endpoint 10.62.201.39:2222, OHOS ARM64, Clang 15, libc++, Conan
2.29.1. Boot identity: bd99f7a0-d41d-46ac-a8f8-bc089feaf6dc; UID 20020084.
Run: libxls-conan-w3-20261015-r6. Both shared and static packages were built from
the original official source archive in one isolated Conan cache.

| Category | Result per link mode | Counting boundary |
|---|---:|---|
| Automake TESTS | 1/1 PASS | test_libxls, actual .trs record |
| Original upstream examples | 2/2 PASS | test2_libxls and test_cpp |
| Installed API consumer | 1/1 PASS | version, workbook, sheet, malformed buffer |
| Installed OHOS CLI workflow | 1/1 PASS | Chinese/space path, exact CSV data, dimensions, missing input |

Upstream total is 3/3; added consumers 2/2; Harmony-specific workflow is one of
the two added cases, not a third added case. Shared/static modes do not double
the test denominator. No skip or expected-failure conversion was used.

The frozen native validator accepted the full twelve-phase receipt chain,
including runner exit, release and postrelease. Full Conan log SHA-256:
`73b35cd9091f76afa6b66811dccb194a58cf0da68b52fd0a742270c6b8adf4d6`.
Collected evidence is under the task-owned libxls-conan-w3-20261015-r6/collected
directory. Earlier failed runs remain separate immutable evidence.

Official skill finish also ran in libxls-finish-w3-20261015-r10. Its unchanged
conan-verify and actual W3 CI substep passed; full collected log SHA-256 is
`715a18796cf319c7ed22d8e99fec6628879950f5115c222ba944ee0a5958716b`.
The frozen native validator accepted all twelve receipts, release and zero
retained task processes. Its generated `.ci-result.json` is copied exactly,
and binds W3 log SHA-256
`efbd45f61ae2bbdd36f63a236103abb594a9c949c4fc27a31e6931100dd4516b`.
The aggregate finish is honestly PARTIAL_POST_W3 because shared pre-existing
knowledge graph warnings remain (step5b/step8); the software candidate includes
its new draft pair and has a separate blocking knowledge/Pre-PR contract.
Earlier failed wrappers remain FAIL and are not used as passing transactions.

Platform AI Review, platform CI and release are not yet completed. Native proof
is not publication evidence.

The r6/r10 runs validate the #93393 checkout transport repair: canonical
Base64/manifest decoding yields identical original bytes (35840), SHA-256
df7d4e07b72284c17ecca138412b48d4217041e5f81a7c297b331c546a20604a.
Both link modes print FIXTURE_EXACT_BYTES_PASS before their original consumers.
Local 4/4 transport checks are not new library runtime cases. Only the binary
PR input representation changed; data and assertions are preserved. Replacement
platform checkout/CI remains to be observed.
