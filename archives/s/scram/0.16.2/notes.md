# scram 0.16.2 适配笔记

## 编译环境
- 构建系统: CMake（C++17，CMAKE_CXX_STANDARD 17）
- 编译日期: 2026-10-07
- 编译器: clang 15.0.4 / clang++（OHOS aarch64-linux-ohos）
- 状态: built（conan-verify G0-G4 + L2/L4/L5 全过）

## 编译步骤

```bash
# 1. conan 依赖注入（制品仓已发布 boost/1.84.0、libxml2/2.15.3.1）
conan install --requires=boost/1.84.0 --requires=libxml2/2.15.3.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  -g CMakeToolchain -g CMakeDeps -of=build

# 2. CMake 配置（关闭可选 Qt5 GUI，关闭上游测试构建）
cmake -S . -B build -DCMAKE_TOOLCHAIN_FILE=build/conan_toolchain.cmake \
  -DCMAKE_PREFIX_PATH=build -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_GUI=OFF -DBUILD_TESTING=OFF

# 3. 构建
cmake --build build -j1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `BOOST_THROW_EXCEPTION_CURRENT_FUNCTION` undeclared | Boost≥1.73 移除该宏（error.hpp 重构） | 替换为 `BOOST_CURRENT_FUNCTION`（patch 0002） |
| 2 | `xmlErrorPtr` 接收 `const xmlError*` 报 discards qualifiers | libxml2 2.15.x 的 `xmlGetLastError()` 返回 const 化 | 变量/参数类型改 `const xmlError*`（patch 0004/0005） |
| 3 | lambda 捕获结构化绑定变量报错 | C++17 禁止在捕获列表引用结构化绑定 | 先定义局部引用变量再捕获（patch 0003） |
| 4 | scram-cli/scram_tests 链接缺 libxml2 符号 | conan CMakeDeps 用 target 方式，传统 `LIBXML2_LIBRARIES` 为空 | 链接补 `LIBXML2_LIBRARY`（patch 0001/0006）+ conanfile generate 注入传统变量 |

## 源码修改

补丁 6 个（archives/s/scram/0.16.2/patches/）：
- 0001: scram-cli 链接补 LIBXML2_LIBRARY
- 0002: BOOST_THROW_EXCEPTION_CURRENT_FUNCTION → BOOST_CURRENT_FUNCTION
- 0003: C++17 结构化绑定 lambda 捕获改用局部引用
- 0004: src/xml.cc 变量类型 const xmlError*
- 0005: src/xml.h GetError 参数 const xmlError*
- 0006: scram_tests 链接补 LIBXML2_LIBRARY

## 依赖版本

- boost/1.84.0（制品仓；含 Boost.DLL header-only 组件，scram env.cc 依赖 program_location）
- libxml2/2.15.3.1（制品仓）
- 注: 制品仓 boost/1.91.0.1.3 为裁剪版（BOOST_INCLUDE_LIBRARIES 不含 dll 组件），scram 需要 boost/dll 头文件，故选用 1.84.0

## 验证结果

```bash
# 上游测试（本地实测，需 Catch2 v2 单头文件 + build/share/scram/*.rng schema）
./scram_tests   # 68 test cases / 525 assertions 全部通过

# 端到端 CLI 验证
./scram --version              # SCRAM 0.16.2（Boost 1_84、libxml2 2.15.3）
./scram input.xml > report.xml # 故障树分析成功，报告含 Minimal Cut Sets

# conan 验证
ohc-run.py conan-verify scram 0.16.2  # G0-G4 + L2/L4/L5 全部 PASS
```
---

**编译结束**: 2026-10-07 09:58
**最终状态**: built
