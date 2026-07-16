# libldac aosp-20250110 adaptation notes

## Result

- Target: OHOS 6.0, armv8, clang 15 profile
- Date: 2026-07-16
- Status: `built`
- Source revision: `eeee1a3f5f8df1282e3a6d297085885fd886737b`
- Source tree: `d5e246f173f24c2e7743af9091a27d1329fcf2ce`
- Source archive SHA-256: `eec6b2ed22273da72cba9413db39476bbf9e148d0b408825dfa25c39fd8e4f06`

## Implementation

The upstream AOSP snapshot provides Android.bp rather than a standalone build
system. `0001-CMakeLists.txt.patch` adds portable CMake targets for the same
`src/ldaclib.c`, `src/ldacBT.c`, and `abr/src/ldacBT_abr.c` source sets. It
installs `libldacBT_enc`, `libldacBT_abr`, and their two public headers.

The recipe verifies both the checked-out Git tree and a deterministic
`git archive` SHA-256 before building, so the pinned AOSP snapshot is
reproducible even though Gitiles is the upstream distribution surface.

No generated configure or build output is stored in the patch.

## Validation

`conan create` completed successfully and produced both static libraries. The
consumer test linked both libraries, allocated encoder and ABR handles,
initialized 48 kHz stereo encoding in SQ mode, and validated the encoder state
through the public APIs before releasing both handles.
