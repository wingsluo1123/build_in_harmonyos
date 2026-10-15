# truecrack 3.5 - HarmonyOS 编译记录

## 概述

truecrack 3.5 是 TrueCrypt 卷密码暴力破解工具（2011 年 Google Code 项目）。
因 HarmonyOS PC 无 NVIDIA GPU，本适配采用 CPU 后端（--enable-cpu）构建，产物为
CLI 可执行文件 bin/truecrack。

**编译状态**: ✅ 通过（构成 CLI 工具，bin/truecrack）

## 编译环境

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS HongMeng Kernel aarch64 |
| 编译器 | clang 15 |
| C 库 | musl libc |
| 构建系统 | autotools（configure + make） |

## 适配要点

- CPU-only 构建：`./configure --enable-cpu --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu`
- 2009 版 config.guess 无法识别 OHOS，需显式 GNU build/host 三元组
- 源码/配置依赖 -fcommon 与旧版 clang 行为，通过补丁修复（见 patches/）
- 6 个官方示例 TrueCrypt 卷（test/）作为上游测试，均恢复出密码
