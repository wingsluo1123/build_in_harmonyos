# prison 6.28.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-10-15
- 编译器: clang/clang++（/data/service/hnp/bin）
- 状态: built

## 编译步骤

1. `conan create archives/p/prison/6.28.0 -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable`
2. 配方 generate() 中 `_sdk_runtime_env()` 前置 SDK `llvm/lib` 与 `aarch64-linux-ohos` 到 LD_LIBRARY_PATH（save_script 覆盖 build/package/test 全阶段），解决 HNP cmake 二进制动态加载 libc++_shared.so 失败
3. 覆写 `self.settings.compiler.cppstd = "20"`：共享 profile 的 `compiler.cppstd=17` 会让 conan_toolchain.cmake 以普通变量强制 `-std=c++17`（优先级高于缓存变量），prison 6.28.0 的 `src/scanner/scanresult.cpp` 使用 C++20 的 `std::ranges`
4. 应用补丁 `patches/0001-fix-ranges-none-of.patch`：OHOS SDK libc++（clang 15 配套）未实现 `std::ranges::none_of`，改用传统 `std::none_of(text.begin(), text.end(), ...)`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Error relocating /data/service/hnp/bin/cmake: _ZTISt12length_error: symbol not found` | HNP cmake 二进制动态加载 SDK `llvm/lib/aarch64-linux-ohos/libc++_shared.so`，LD_LIBRARY_PATH 未包含该目录 | generate() 中 `_sdk_runtime_env()` 前置 SDK lib 目录 + save_script 覆盖 build/package/test 全阶段（与 ecm 6.28.0 同源方案） |
| 2 | `scanresult.cpp: no member named 'ranges' in namespace 'std'` | 共享 profile `compiler.cppstd=17` → conan_toolchain.cmake 普通变量强制 `-std=c++17`，缓存变量 `CMAKE_CXX_STANDARD=20` 被覆盖 | generate() 中覆写 `self.settings.compiler.cppstd = "20"`，toolchain 直接生成 `CMAKE_CXX_STANDARD 20` |
| 3 | `scanresult.cpp: no member named 'none_of' in namespace 'std::__n1::ranges'` | OHOS SDK 配套 libc++（clang 15）未实现 `std::ranges::none_of`（ranges 算法不完整） | 打补丁改用传统 `std::none_of(text.begin(), text.end(), ...)`（text() 返回 std::string） |
| 4 | CI: `Check for working C compiler: /data/service/hnp/bin/clang - broken`，`make ... resource temporarily unavailable` | CI 环境下 make jobserver（FIFO/资源）受限，CMake TryCompile 编译器检查失败（本地环境未触发） | `_library_runtime_env()`/`_sdk_runtime_env()` 中 `MAKEFLAGS=""`、`MFLAGS=""`、`CMAKE_BUILD_PARALLEL_LEVEL=1`，禁用 jobserver 并强制串行 |

## 源码修改

- `patches/0001-fix-ranges-none-of.patch`：`src/scanner/scanresult.cpp` 中 `std::ranges::none_of(zxRes.text(), ...)` → `const auto &text = zxRes.text(); std::none_of(text.begin(), text.end(), ...)`

## 依赖版本

- ECM 6.28.0（build tool_requires）
- qtbase/6.11.1（Qt6 Core Gui）
- qrencode/4.1.1（QRencode 必需）
- qtmultimedia/6.11.1（WITH_MULTIMEDIA=ON）
- zxing-cpp/2.3.0（WITH_ZXING=ON，scanner 依赖）
- libdmtx/0.7.5（WITH_DMTX=ON）

## 验证结果

```bash
# conan create 主包
conan create archives/p/prison/6.28.0 -pr:h=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# → PASS（source/configure/build/install 全通过）

# 上游测试（BUILD_TESTING=ON，ctest 由配方 _run_upstream_tests 集成）
# → 100% tests passed, 0 tests failed out of 8
#   （prison-aztecbarcodetest / prison-reedsolomontest / prison-code128barcodetest /
#     prison-datamatrixtest / prison-qrtest / prison-zxingutiltest /
#     prison-imagescannertest / prison-mecardtest）

# test_package
# → CMake configure + build(test_prison) + test() 运行 test_prison 通过（QRCode 图像生成断言）
```

## 交付物

- `libKF6Prison.so` + `libKF6PrisonScanner.so`（shared）
- CMake config: `KF6PrisonConfig.cmake`（`cpp_info.builddirs = lib/cmake`）

## 注意事项

- `WITH_QUICK=OFF`（Qt Quick 组件不构建，qtdeclarative 可选依赖不强制）；`WITH_MULTIMEDIA=ON`（scanner 支持，需 qtmultimedia）
- `KF_IGNORE_PLATFORM_CHECK=TRUE`（CMake 不识别 HarmonyOS 平台）
- `KF_SKIP_PO_PROCESSING=ON`（跳过翻译处理）
- `CMAKE_BUILD_RPATH=$ORIGIN` + `-Wl,--disable-new-dtags`（运行时依赖库从 $ORIGIN 解析）
---

**编译结束**: 2026-10-16 09:41
**最终状态**: built
