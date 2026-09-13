# nsnake 3.0.1.1 适配笔记

## 编译环境
- 构建系统: Makefile
- 编译器: clang/clang++ 15.0.4
- 目标平台: OHOS aarch64
- 状态: built

## 编译步骤
Conan 配方通过官方 v3.0.1 源码归档构建，使用 Conan 依赖 `ncurses/6.4`，并以 `make -j1` 生成 `bin/nsnake`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `KEY_CTAB` 与 `KEY_ENTER` 重复 case | OHOS ncurses 头文件为两个键定义相同数值 | 仅在两值不同时编译 `KEY_CTAB` 分支 |
| 2 | 初始化模板误判构建系统/依赖 | 项目是 Makefile，非 Autotools，且依赖未被自动识别 | 按历史成功配方固化 Makefile 构建与 `ncurses/6.4` |

## 源码修改
`patches/0001-src-Flow-InputManager.cpp.patch` 条件化重复 ncurses key case。

## 依赖版本
- `ncurses/6.4`

## 验证结果
详见 `reports/test-report.md`，包含上游 `make check` 结果和消费者测试结果。
---

**编译结束**: 2026-09-13 18:52
**最终状态**: built
