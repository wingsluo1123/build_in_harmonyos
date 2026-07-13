# ittapi

Intel Instrumentation and Tracing Technology (ITT) API

## 简介

ittapi 是 Intel 提供的性能分析基础库，用于在用户程序中插入标注信息，供 Intel 性能分析工具（如 VTune Profiler）收集运行时数据。主要功能包括：

- 线程分析标注 (Threading Tools)
- 帧率/区域/任务标注
- JIT 分析 (JIT Profiling)
- 内存分配跟踪

## 版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 3.26.7 | published | 2026-06-26 |

## 许可证

GPL-2.0-only OR BSD-3-Clause

## 构建系统

CMake

## 编译产物

- `libittnotify.a` — 静态库（包含 ittnotify_static.c 和 jitprofiling.c）
- 头文件: ittnotify.h, jitprofiling.h, libittnotify.h, advisor-annotate.h, ittnotify-zca.h

## 依赖

无外部依赖。自包含静态库。

## 主页

https://github.com/intel/ittapi
