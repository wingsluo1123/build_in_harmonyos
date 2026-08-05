# crosstool-ng 1.28.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-06
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 初始化编译：`ohc-run.py init-build crosstool-ng 1.28.0`
2. 应用补丁：3 个补丁（configure, config.guess, config.sub）
3. 配置：`./configure --prefix=$DEFAULT_PREFIX`
4. 编译：`make -j1`
5. 安装：`make install DESTDIR=$TEST_PREFIX`
6. 测试：`make check`（通过，无测试用例）
7. Conan 配方生成：`ohc-run.py conan-init`
8. Conan 验证：`ohc-run.py conan-verify`（全部通过）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 失败：缺少 makeinfo | texinfo 未安装 | 安装 texinfo 7.3 预编译包，从 texinfo 源码提取 Perl 模块 |
| 2 | configure 失败：缺少 help2man | help2man 未安装 | 安装 help2man 1.49.3 预编译包 |
| 3 | configure 失败：缺少 libtool | libtool 未安装 | 从 conan ohpcd 仓安装 libtool 2.5.4 |
| 4 | configure 失败：找不到 curses.h | ncurses 预编译包缺少头文件 | 从 ncurses 6.4 源码生成完整头文件 |
| 5 | HMDFS 权限错误 | umask 077 导致权限问题（E011） | 修改 configure 中 umask 077 为 umask 022 |
| 6 | 平台不识别 | config.guess 缺少 HarmonyOS 识别（E007） | 添加 ohos 平台识别补丁 |

## 源码修改

生成 3 个补丁文件：

| 补丁文件 | 说明 |
|---------|------|
| 0001-configure.patch | 修改 umask 077 为 umask 022（解决 E011 HMDFS 权限问题） |
| 0002-scripts-config.guess.patch | 添加 HarmonyOS 平台识别（解决 E007） |
| 0003-scripts-config.sub.patch | 添加 ohos 三元组验证（解决 E072） |

所有补丁均为平台适配修改，无功能改动。

## 依赖版本

| 软件 | 版本 | 说明 |
|------|------|------|
| texinfo | 7.3 | makeinfo 工具（预编译包不完整，从源码提取 Perl 模块） |
| help2man | 1.49.3 | 帮助文档生成工具 |
| ncurses | 6.4 | curses 库（预编译包缺少头文件，从源码生成） |
| libtool | 2.5.4 | GNU libtool（从 conan ohpcd 仓安装） |

## 验证结果

- conan create: PASSED（G2 干净构建通过）
- conan-verify: 全部通过（G1-G4, L2/L4/L5）
- W3 本地 CI 模拟: PASSED
- ct-ng --version: GNU Make 4.4.1 (Built for aarch64-unknown-linux-gnu)

## 注意事项

1. crosstool-ng 是 Make wrapper (ct-ng)，不是典型二进制文件
2. texinfo 预编译包缺少 Perl 模块，需从 texinfo 源码提取
3. ncurses 预编译包缺少头文件，需从 ncurses 源码生成
4. libtool 从 conan ohpcd 仓安装
---

**编译结束**: 2026-08-06 06:28
**最终状态**: published
