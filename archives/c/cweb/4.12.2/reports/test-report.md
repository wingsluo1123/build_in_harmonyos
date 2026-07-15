# Test Report — cweb 4.12.2

## Build Test

### Bootstrap Compilation
- ✅ `make ctangle` — ctangle compiled successfully from ctangle.c + common.c
- ✅ ELF signing of ctangle — binary-sign-tool succeeded
- ✅ `make cweave` — ctangle generated cweave.c, then compiled cweave
- ✅ ELF signing of cweave — binary-sign-tool succeeded

### Functional Tests
- ✅ `ctangle wc` on examples/wc.w → wc.c (215 lines)
- ✅ `cweave wc` on examples/wc.w → wc.tex (342 lines)

### Conan Package Test
- ✅ `conan create` — recipe builds from source (conan create + test_package)
- ✅ test_package/test.sh — ctangle hello.w → hello.c (9 lines), cweave hello.w → hello.tex (16 lines)

## CI Local Simulation (W3)
- ✅ setup.sh — passed
- ✅ build_and_test.sh — passed (L0-L5 gates)

## Known Limitations
- `make cautiously` (self-replication test) requires ELF-signed ctangle during build process
- G0 clean build verification cannot insert signing step during automated `make` — known platform limitation (E077/E135)
