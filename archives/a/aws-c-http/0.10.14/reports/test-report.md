# Test Report: aws-c-http 0.10.14

## Build Information
- **Build System**: CMake
- **Compiler**: clang 15.0.4
- **Platform**: OHOS aarch64
- **Build Type**: Release (static)
- **Date**: 2026-08-05

## Dependencies
| Package | Version | Status |
|---------|---------|--------|
| aws-c-common | 0.12.6 | Built locally (conan create) |
| aws-c-cal | 0.9.13 | Built locally (conan create) |
| aws-c-compression | 0.3.2 | Built locally (conan create) |
| aws-c-io | 0.26.3 | Built locally (conan create, BYO_CRYPTO=ON) |

## Conan Create Result
- **Status**: SUCCESS
- **Package**: aws-c-http/0.10.14
- **Binary ID**: 78aa0a2306a423f2f6c4c7a090066996bcc255f5
- **Test Package**: PASSED

## Test Package Results
```
aws-c-http library initialized: OK
aws-c-http library cleaned up: OK
```

## Notes
- aws-c-io uses BYO_CRYPTO=ON to skip s2n-tls dependency
- aws-c-io uses CMAKE_SYSTEM_NAME=Linux for posix/epoll code path
- aws-c-cal include dirs require manual -I flag workaround (CMakeDeps bug)
- test_package uses forward declarations to avoid header include issues
