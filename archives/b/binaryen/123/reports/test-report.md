# Test Report — binaryen 123

## Build Verification
- **Build System**: CMake
- **Compiler**: clang 15.0.4 / clang++ 15.0.4
- **Build Type**: Release
- **Status**: ✅ PASS

## CMake Options
- `-DBUILD_STATIC_LIB=ON` — static library to avoid OHOS RPATH issues
- `-DBUILD_TESTS=OFF` — disabled tests (googletest submodule not in source tarball)

## Test Results
- **conan create**: ✅ PASS (100% tests passed)
- **test_package**: ✅ PASS (test_binaryen: BinaryenModuleCreate + BinaryenModulePrint OK)
- **smoke test** (wasm-opt --version): ✅ PASS (wasm-opt version 123)

## Binary Verification
- `readelf -d wasm-opt` shows only `libc.so` and `libc++_shared.so` as NEEDED
- No libbinaryen.so dependency (static build)
- No RPATH issues
