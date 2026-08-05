# czmq 4.2.1 — Build Notes

> Build date: 2026-08-06
> Status: published
> Build system: cmake

## Basic Info
| Item | Value |
|------|-------|
| Software | czmq |
| Version | 4.2.1 |
| Source | https://github.com/zeromq/czmq/releases/download/v4.2.1/czmq-4.2.1.tar.gz |
| Dependency | zeromq/4.3.5 |
| Build system | cmake |
| Compiler | clang 15.0.4 |
| Platform | HarmonyOS aarch64 |

## Build Steps
1. Downloaded source tarball
2. Applied patch: 0001-CMakeLists.txt.patch (fix cmake_minimum_required for CMake 4.x)
3. cmake configure with CMAKE_POLICY_VERSION_MINIMUM=3.5
4. make -j2 build succeeded
5. make install succeeded

## Issues Encountered
- CMake 4.x removed support for cmake_minimum_required < 3.5, fixed by patch
- CMakeDeps on OHOS doesn't propagate zeromq include dirs; workaround in test_package CMakeLists.txt
- zstr_dup not available in czmq 4.2.1, simplified test to use zhash API only

## Final Status
Build: SUCCESS
Conan verify: PASS

## 最终状态
- 编译结束: 2026-08-06
- COMPLETED
