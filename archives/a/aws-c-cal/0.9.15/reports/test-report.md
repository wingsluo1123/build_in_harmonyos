# Test Report — aws-c-cal 0.9.15

## Build Information
- **Software**: aws-c-cal
- **Version**: 0.9.15
- **Build System**: CMake
- **Build Date**: 2026-07-27
- **Compiler**: clang 15.0.4
- **Platform**: HarmonyOS aarch64 (armv8)
- **Build Type**: Release (shared library)

## Build Commands
```bash
source .build-context-aws-c-cal-0.9.15
cd $BUILD_SRC_DIR
AWS_COMMON=/storage/Users/currentUser/.conan2/p/b/aws-c01de038095334/p
AWS_LC=/storage/Users/currentUser/.conan2/p/b/aws-l9bf37065f71fa/p
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON \
  -DBUILD_TESTING=OFF -DUSE_OPENSSL=OFF \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_PREFIX_PATH="$AWS_COMMON;$AWS_LC"
cmake --build build -j$(nproc)
cmake --install build --prefix $TEST_PREFIX
```

## Build Result
- **Status**: SUCCESS
- **Output**: `libaws-c-cal.so` (ELF shared object, 64-bit LSB arm64)
- **NEEDED libraries**:
  - `libaws-c-common.so` (from aws-c-common conan package, dynamic)
  - `libc.so` (system)
  - `libcrypto.a` from aws-lc is statically linked (not shown as NEEDED)

## Patch Applied
- `patches/0001-CMakeLists.txt.patch`: Add `find_package(Threads REQUIRED)` before `find_package(crypto REQUIRED)` to resolve missing `Threads::Threads` target. The aws-lc crypto-config.cmake depends on Threads::Threads.

## Dependencies
- aws-c-common/0.14.3@ohpcd/stable (dynamic library libaws-c-common.so)
- aws-lc/5.4.0@ohpcd/stable (static library libcrypto.a + libssl.a, OPENSSL_NO_ASM=ON)

## Conan Verify Result
- **G0**: PASS (knowledge graph hit E092 - CMake HarmonyOS platform warning, non-blocking)
- **G1**: PASS (recipe completeness)
- **G2**: PASS (conan create from clean source)
- **G3**: PASS (system same-name library isolation R26)
- **G4**: PASS (product completeness)
- **L2**: PASS (smoke test)
- **L4**: PASS (checksec security scan)
- **L5**: PASS (product baseline comparison)

## Test Package
- **test.c**: Computes SHA-256 hash of "hello world" using aws-c-cal API
- **Result**: Test binary compiled and linked successfully

## Conclusion
aws-c-cal 0.9.15 builds successfully on HarmonyOS aarch64 platform with aws-lc as crypto backend.
