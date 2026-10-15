# indi-starbook-ten

INDI 天文框架的 Vixen StarBook Ten 望远镜 mount 控制器驱动。

- **上游**: https://github.com/indilib/indi-3rdparty
- **源码包**: Debian `indi-starbook-ten_0.1.orig.tar.gz`
- **构建系统**: CMake
- **语言**: C++（含内置 cpp-httplib 单头）
- **产出**: 可执行程序 `indi_starbook_ten`（INDI 驱动，非库）

## 简介

indi-starbook-ten 是 INDI（Instrument Neutral Distributed Interface）天文
设备控制框架的一个驱动，用于控制 Vixen StarBook Ten 望远镜 mount
（固件 >= 5.10）。mount 通过 HTTP 协议（StarBook 命令集）驱动，核心为
`starbook_ten.cpp/h` 协议客户端 + 内置 `httplib.h`，依赖已发布的
`libindi` 与 `libnova`。

## 鸿蒙（OHOS）适配

- CMake 强制 `CMAKE_SYSTEM_NAME=Linux`（E092：CMake 不识别 HarmonyOS）。
- 上游 `cmake_minimum_required(VERSION 3.0)` → 注入
  `CMAKE_POLICY_VERSION_MINIMUM=3.5`（CMake 4.x 兼容）。
- 使用驱动自带的 `FindINDI.cmake` / `FindNova.cmake`，配方注入依赖路径。
- C++ 目标链接 OHOS libc++（`c++`/`c++abi`）。

## 依赖

| 依赖 | 版本 | 制品仓 |
|------|------|--------|
| libindi | 2.2.2.1 | ✅ 已发布 |
| libnova | 0.16 | ✅ 已发布 |

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.1 | built | 初始 Conan 配方适配 |
