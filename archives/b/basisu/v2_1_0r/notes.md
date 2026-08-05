# Basis Universal v2_1_0r Adaptation Notes

## Build Environment
- Build system: CMake
- Build date: 2026-08-05
- Compiler: clang/clang++
- Status: built (conan adaptation added)

## Build Steps

1. Download basis_universal v2_1_0r source from GitHub
2. Apply qsort_r compatibility patches:
   - patches/0001-zstd-zstd.c.patch: qsort_r fix for zstd.c
   - patches/0002-zstd-zstddeclib.c.patch: qsort_r fix for zstddeclib.c
3. Build with CMake

## Key Adaptation: qsort_r Compatibility
- Bundled zstd library uses qsort_r() (GNU extension) not available in OHOS musl libc
- Fix: Add `&& defined(HAS_QSORT_R)` guard to prevent _GNU_SOURCE definition
- On non-OHOS: conanfile.py generate() sets -DHAS_QSORT_R
- On OHOS: HAS_QSORT_R not set, code falls back to C90 qsort() with global context

## Deliverables

| File | Description |
|------|-------------|
| conanfile.py | Conan recipe |
| conandata.yml | Source + patch declarations |
| test_package/ | L1 test (upstream basisu -test + consumer link test) |
| patches/0001-zstd-zstd.c.patch | qsort_r compatibility for zstd.c |
| patches/0002-zstd-zstddeclib.c.patch | qsort_r compatibility for zstddeclib.c |
---

**编译结束**: 2026-08-06 00:47
**最终状态**: published
