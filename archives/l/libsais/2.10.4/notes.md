# libsais 2.10.4 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-26
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码: `https://github.com/IlyaGrebnov/libsais/archive/refs/tags/v2.10.4.tar.gz`
2. 解压到工作目录
3. CMake 配置:
   ```bash
   cd $BUILD_SRC_DIR && mkdir build && cd build
   cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_SHARED_LIBS=OFF
   ```
4. 编译: `make -j1`
5. Staging 安装: `make install DESTDIR=$TEST_PREFIX`
6. 默认安装: `make install`
7. Conan 配方生成: `ohc-run.py conan-init libsais 2.10.4`
8. Conan 验证: `ohc-run.py conan-verify libsais 2.10.4`
9. 收尾: `ohc-run.py finish libsais 2.10.4 published`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-init 生成的 conanfile.py 使用 Autotools 模板 | init-build 自动检测构建系统为 autotools（误判） | 手动将 conanfile.py 重写为 CMake 模板（使用 CMake, CMakeToolchain, cmake_layout） |
| 2 | conandata.yml 的 sha256 为占位符 | conan-init 未自动计算 | 手动计算 tarball sha256 并填入: `94aa88f9e29f8812214ecfa6b55f5dca14c7d8a427409c062f734a61ca4c6931` |
| 3 | test_package 的 test.c 是空壳（不调用任何 libsais 函数） | 模板生成的占位代码 | 编写实际测试：调用 `libsais()` 构造 "banana" 的后缀数组，验证结果为 [5,3,1,0,4,2] |
| 4 | G2 conan-verify 失败: "Library 'libsais' not found in package" | libsais 的 CMakeLists.txt 设置 `PREFIX ""`，库文件名为 `libsais.a`（无 `lib` 前缀）；Conan CMakeDeps 的 `find_library(NAMES libsais)` 默认查找 `liblibsais.a`（带 `lib` 前缀），找不到 `libsais.a` | 在 test_package/CMakeLists.txt 中添加 `list(APPEND CMAKE_FIND_LIBRARY_PREFIXES "")`，使 find_library 也搜索无前缀的文件名 |
| 5 | test_package conanfile.py 的 CMakeToolchain 冲突 | 在 `generators` 属性和 `generate()` 方法中同时声明 CMakeToolchain | 从 `generators` 中移除 `CMakeToolchain`，仅在 `generate()` 方法中手动创建并设置 CMAKE_SYSTEM_NAME=Linux (E092) |

## 源码修改

无上游源码修改。所有修改均在 Conan 配方文件中：
- `conanfile.py`: 从 Autotools 模板重写为 CMake 模板，添加 E092 修复
- `test_package/CMakeLists.txt`: 添加 CMAKE_FIND_LIBRARY_PREFIXES/SUFFIXES 修复
- `test_package/conanfile.py`: 添加自定义 generate() 方法
- `test_package/test.c`: 编写实际功能测试
- `conandata.yml`: 填入正确 sha256

## 依赖版本

无外部依赖。libsais 是纯 C 库，仅需标准 C 编译器。

## 验证结果

```bash
# 静态链接验证
$ readelf -d libsais.a
# 所有 .obj 均无动态段 (No dynamic section)

# Conan test_package 测试
$ conan create ... (test_package)
100% tests passed, 0 tests failed out of 1
# 输出: test libsais 2.10.4: OK

# Conan 8道门禁
G0: PASS | G1: PASS | G2: PASS | G3: PASS | G4: PASS | L2: PASS | L4: PASS | L5: PASS
```

## 注意事项

1. **E092 (HarmonyOS 平台不识别)**: CMake 不认识 HarmonyOS 作为目标平台。conanfile.py 的 generate() 中设置 `CMAKE_SYSTEM_NAME=Linux` 和 `CMAKE_SYSTEM_PROCESSOR=aarch64` 作为修复。test_package 的 conanfile.py 也需要同样处理。

2. **PREFIX "" 问题**: libsais 的 CMakeLists.txt 设置 `PREFIX ""` 导致库文件名为 `libsais.a`（而非标准的 `liblibsais.a`）。Conan CMakeDeps 的 `find_library` 默认只搜索带 `lib` 前缀的文件。修复方法是在 test_package/CMakeLists.txt 中 `list(APPEND CMAKE_FIND_LIBRARY_PREFIXES "")`。

3. **上游无测试套件**: libsais 2.10.4 的 CMakeLists.txt 未定义任何测试目标。test_package 中编写的 L1 测试（验证 `libsais()` 函数）替代了上游测试。

---

**编译结束**: 2026-06-26 05:00
**最终状态**: published
