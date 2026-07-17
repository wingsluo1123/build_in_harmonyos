# avro-c 1.12.1 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-07-15
- 状态: built（配方已生成，待 CI 验证）

## 基本信息
| 项目 | 值 |
|------|-----|
| 软件 | avro-c |
| 版本 | 1.12.1 |
| 源码 URL | https://archive.apache.org/dist/avro/avro-1.12.1/c/avro-c-1.12.1.tar.gz |
| SHA256 | b64e31b94719499549622aa92f1d96d1742967ced261a0931b63be3bbe907f2c |
| 构建系统 | CMake |
| 依赖 | jansson/2.15.0, snappy/1.2.2, xz/5.6.2, zlib/1.3.1 |

## 历史编译记录（1.12.0）
- 2026-04-24~25: 手动编译成功，26/26 测试通过
- 使用完整 Apache Avro tarball 保留 share 目录（测试数据）
- 4 个已知问题已通过补丁解决

## 补丁
1. **0001-CMakeLists.txt.patch**: CMake UNIX 检测（为 HarmonyOS 设置 UNIX 标志，使 version.sh 正常执行获取 SOVERSION）
2. **0002-version.sh.patch**: bash 路径修复（#!/bin/bash → #!/usr/bin/env bash）

## Conan 配方要点
- 依赖: jansson/2.15.0, snappy/1.2.2, xz/5.6.2, zlib/1.3.1
- generate(): 添加 CMAKE_EXE_LINKER_FLAGS=-lc++（snappy 是 C++ 库）
- R33: 使用 CMakeToolchain 自动管理，无硬编码环境变量
- R34: test_package 调用 avro API（schema 解析 + record 序列化/反序列化）
- R37: 版本号 = 上游版本 1.12.1
- R38: 命令行工具（avroappend, avrocat, avromod, avropipe），已创建 commands.json

## 产物
- 库: libavro (lib/avro.h)
- 可执行文件: avroappend, avrocat, avromod, avropipe
