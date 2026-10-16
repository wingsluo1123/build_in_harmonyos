# indi-rtklib

INDI 天文框架的 RTKLIB 精密定位驱动。

- **上游**: https://github.com/indilib/indi-3rdparty
- **源码包**: Debian `indi-rtklib_1.0+20221222172722.orig.tar.gz`
- **构建系统**: CMake
- **语言**: C / C++
- **产出**: 可执行程序 `indi_rtklib`（INDI 驱动，非库）

## 简介

indi-rtklib 是 INDI（Instrument Neutral Distributed Interface）天文设备
控制框架的一个驱动，用于通过 RTKLIB 实现精密定位。它由
`rtklib_driver.cpp`（继承 `INDI::GPS`）和独立的 C 解析器
`rtkrcv_parser.c` 组成，**不打包 RTKLIB 算法源码本身**，依赖已发布的
`libindi` 与 `libnova`。

## 鸿蒙（OHOS）适配

- CMake 强制 `CMAKE_SYSTEM_NAME=Linux`（E092：CMake 不识别 HarmonyOS）。
- 使用驱动自带的 `FindINDI.cmake` / `FindNova.cmake`，配方注入依赖路径。
- C++ 目标链接 OHOS libc++（`c++`/`c++abi`）。

## 依赖

| 依赖 | 版本 | 制品仓 |
|------|------|--------|
| libindi | 2.2.2.1 | ✅ 已发布 |
| libnova | 0.16 | ✅ 已发布 |
| zlib | 1.3.1.1 | ✅ 已发布 |

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.0-20221222172722 | built | 初始 Conan 配方适配 |
