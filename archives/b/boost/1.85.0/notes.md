# Boost 1.85.0 适配笔记

## 编译环境

- 构建系统：Boost.Build engine 自定义构建脚本
- 编译日期：2026-07-13
- 编译器：clang/clang++ 15.0.4
- 平台：HarmonyOS PC aarch64
- 状态：built（本地 Conan 验证通过，尚未由 CI 上传）

## 编译步骤

1. W0 预检：`bash ci/scripts/preflight_check.sh boost/1.85.0`，无外部依赖。
2. 下载官方 Boost 1.85.0 tarball 并校验 SHA256。
3. 在 `tools/build/src/engine` 执行 `./build.sh clang`，生成 b2 5.1.0。
4. 执行 `b2 --help` 验证 CLI。
5. 从 Conan profile 读取 clang/clang++ 绝对路径并生成 `user-config.jam`，执行 `b2 toolset=clang-ohos -j1`，编译并运行 `hello.c`。
6. 由 Conan 配方重复上述干净构建与消费者测试。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `b2 --version` 输出版本后返回 1 | Boost.Build 5.1.0 的该选项退出码行为 | 门禁使用 `b2 --help`，并增加实际构建 hello 项目的功能测试 |
| 2 | 旧版 1.84.0 记录称 b2 的 SHELL 机制不可用 | 旧记录测试的是完整 Boost 库构建，不等同于 b2 engine 自身 | 本次直接构建 engine，并用 b2+clang 完成实质消费者构建验证 |

## 源码修改

无。Boost.Build engine 在 HarmonyOS PC aarch64 上无需源码补丁。

## 依赖版本

无外部 Conan 依赖；构建时使用系统 clang/clang++ 15.0.4。

## 验证结果

```text
B2 5.1.0 (OS=LINUX, jobs=20)
ELF64, AArch64, PIE
b2 --user-config=user-config.jam toolset=clang-ohos -j1 -> hello
hello output: boost-b2-ok
```

## 注意事项

本配方交付 Boost 1.85.0 源码中的 Boost.Build `b2` 命令行工具，不宣称交付全部需要编译的 Boost C++ 库。
---

**编译结束**: 2026-07-13 10:59
**最终状态**: built
