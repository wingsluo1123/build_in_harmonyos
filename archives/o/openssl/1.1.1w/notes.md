# OpenSSL 1.1.1w OHOS adaptation

## Build

- Target: `openharmony-aarch64`
- Build system: Perl `Configure` and Make
- Configuration: `no-asm`, static libraries only, `-fPIC -O2 -D__OHOS__`
- Source checksum: `cf3098950cb4d853ad95c0841f1f9c6d3dc102dccfcacd521d93925208b76ac8`

## Adaptation

- Added the OpenHarmony aarch64 Configure target through a source patch.
- Kept the Configure compatibility patch required by the OHOS toolchain.
- Resolves compiler and archiver paths from Conan configuration when provided.
- The package disables assembly by default because the OHOS target requires the portable implementation.

## Tests

- The Conan consumer test checks the packaged version, SHA-256, SSL context creation, and AES-256-CBC round-trip.
- Remote OHOS CI passed on job `20260727-023111-2a31de-openssl-111w-final-test` at commit `3c59deb48`.
- Conan create completed successfully on OHOS/aarch64; upstream tests and the consumer test passed (`4/4`).
- L0, L1, L4, and L5 passed. L2 was non-blocking because the packaged command smoke probes could not run on OHOS.
