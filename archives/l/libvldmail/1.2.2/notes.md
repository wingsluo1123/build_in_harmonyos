# libvldmail 1.2.2 适配笔记

## 编译环境
- 构建系统: cmake（C99 纯 C 库，CMake >= 3.12）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4（aarch64-linux-ohos，OHOS profile）
- 状态: built

## 编译步骤

1. conan create `-pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`
2. CMake 配置：`-DLIBVLDMAIL_TESTS=OFF`（库构建）；测试构建另用 `-DLIBVLDMAIL_TESTS=ON` 生成 vldmailtest
3. 上游测试：`ctest --test-dir build-tests -C Debug` → 1/1 通过；直接运行 vldmailtest → 11/11 ok

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-init 生成 autotools 模板 | 构建系统误判（上游为 CMake） | 重写 conanfile.py 为 CMakeToolchain/CMake 配方 |
| 2 | conandata.yml sha256 占位符 | 模板未回填 | 填官方归档 SHA-256：1cea5431b8c555959c2640faa64ed8d3e078044590f2c384b14f4db443ef8e0d |

## 源码修改

无源码补丁（patches/ 为空）；仅配方与测试文件。

## 依赖版本

无第三方依赖。

## 验证结果

- conan-verify：G1-G4 全过，L2/L4/L5 通过，判定可 published
- test_package 消费者测试（OHOS profile armv8）：1/1 Passed
- 上游测试：ctest 1/1 Passed；vldmailtest 11/11 ok（autotest-cases 台账）
- W3 本地 CI 模拟：通过（含基线隔离复验审计）
---

**编译结束**: 2026-09-27 19:40
**最终状态**: built
