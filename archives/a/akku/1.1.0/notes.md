# Adaptation Notes - akku 1.1.0

## Overview
Akku.scm 是 Scheme 语言包管理器（CLI 工具），基于 GNU Guile 2.2/3.0。
构建系统：Autotools（configure + make）。

## Build System
- Autotools（configure.ac + Makefile.am），`GUILE_PKG([3.0 2.2])` + `GUILE_PROGS`
- configure 硬性要求 `guild` 二进制与 `guile-2.2.pc`（PKG_CHECK_MODULES）

## 依赖（制品仓，别人发布）
- guile/2.2.7（PR #470 合并发布）——本机验证时用本地构建的修复版 guile
  （含 prebuilt ccache 复制逻辑，R34 compile+link 通过）

## Build Process
1. 下载 GitLab 官方 sdist `akku-1.1.0.tar.gz`
2. 应用补丁：0001-configure-umask（configure 临时目录 umask 077→022，HMDFS）
3. configure + make -j1
4. make install DESTDIR=package
5. test_package: `akku version` 输出 1.1.0

## OHOS 关键问题与解决
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status: Permission denied | HMDFS umask 077 | 补丁 0001：configure 临时目录 umask 077→022 |
| 2 | guild compile: no such language bytecode | guile 2.2 用 GUILE_LOAD_COMPILED_PATH 查 .go（GUILE_CCACHE_DIR 是 3.0 变量） | akku generate() 注入 GUILE_LOAD_COMPILED_PATH 指向 guile ccache |
| 3 | guild compile: Unbound variable: compile-file / no code for module (ice-9 optargs) | OHOS 上 guile 自动编译失败 | 设 GUILE_AUTO_COMPILE=0，guild 直接使用 ccache 字节码 |
| 4 | guild: //bin/guile: inaccessible | guild 脚本 ${GUILE:-//bin/guile} 回退路径无效（prefix=/） | 显式 env.define("GUILE", guile_bin) |
| 5 | configure: Error loading libguile-2.2.so.1 | configure 运行 guile 时 LD_LIBRARY_PATH 不含 guile lib | 注入 guile 包 lib 到 LD_LIBRARY_PATH |
| 6 | akku --version: Missing required argument | akku CLI 用 version 子命令（srfi-37 args-fold） | test_package 改用 `akku version` |
| 7 | no code for module (industria strings) | akku 自身模块目录未加入 GUILE_LOAD_PATH | package_info() 注入 share/akku/guile/site/2.2 |

## 依赖版本
| 软件 | 版本 | 说明 |
|------|------|------|
| guile | 2.2.7 | 制品仓（PR #470），本机验证用修复版（prebuilt ccache） |

## 验证结果
```bash
$ akku version
1.1.0
```
conan-verify: G1/G2/G3/G4 + L2/L4/L5 全 PASS。

## 交付物
| 文件 | 说明 |
|------|------|
| 0001-configure-umask.patch | configure umask 077→022（HMDFS） |

## 注意事项
1. guile 2.2 字节码路径变量是 GUILE_LOAD_COMPILED_PATH，不是 GUILE_CCACHE_DIR
2. OHOS 必须 GUILE_AUTO_COMPILE=0（自动编译失败）
3. akku 版本输出用 `akku version` 子命令
---

**编译结束**: 2026-08-09 06:28
**最终状态**: built
