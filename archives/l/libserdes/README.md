# libserdes

Confluent Schema-Registry C/C++ 客户端库，提供基于 Avro 的序列化/反序列化能力。libserdes 使用 Avro schema 对数据进行序列化和反序列化，并与 Confluent Schema Registry 集成实现集中式 schema 管理。

## 概述

libserdes 由 Confluent 开发，是 Confluent Platform 的组成部分。主要功能：

- C 和 C++ 的 Avro schema 序列化/反序列化
- 与 Confluent Schema Registry 集成，自动注册和查找 schema
- Schema 帧封装（与 Confluent Java/Python serdes 线兼容的传输格式）
- 同时支持动态库（`.so`）和静态库（`.a`）构建
- 支持 pkg-config（`serdes.pc` / `serdes-static.pc`）

## 上游信息

- **仓库地址**: https://github.com/confluentinc/libserdes
- **许可证**: Apache-2.0

## 构建系统

libserdes 使用 **mklove** —— 一种自定义的类 autotools 构建系统（非标准 autotools）。`configure` 脚本位于源码根目录且自包含。与标准 autotools 的主要区别：

- 无需 `autoreconf` / `autoconf`
- 直接运行 `./configure --prefix=...` 即可
- `make` / `make install` / `make check` 遵循标准约定
- `config.h` 和 `Makefile.config` 由 configure 生成

## 依赖

| 依赖 | 必需 | 说明 |
|------|------|------|
| jansson | ✅ | JSON 解析（avro schema 表示） |
| libcurl | ✅ | HTTP 客户端，用于 Schema Registry 通信 |
| avro-c | ✅ | Avro 序列化/反序列化核心 |
| librdkafka | ❌ | 可选，用于 Kafka 集成（OHOS 构建中已禁用） |
| avro-cpp | ❌ | 可选 C++ Avro 绑定（OHOS 构建中已禁用） |

## OHOS 适配

### 关键要点
- avro-c 在 OHOS 上无预编译包，需从 Apache Avro 源码手动编译
- avro-c CMake 4.x 不兼容：需添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`
- avro-c `version.sh` 在 HarmonyOS 上执行失败：需在 CMakeLists.txt 中硬编码版本变量作为 fallback
- 下载源码时 SSL 证书路径不匹配：设置 `SSL_CERT_FILE` 环境变量解决
- pkg-config 名称为 `serdes`（非 `libserdes`），链接使用 `-lserdes`
- `make -j2` 可能出现 `jobserver mkfifo` 警告 —— HarmonyOS tmpfs 已知限制，不影响构建

### 已适配版本
- **8.3.0** — ✅ 已发布（2026-07-06）

## 参考链接
- [GitHub 仓库](https://github.com/confluentinc/libserdes)
- [Confluent 文档](https://docs.confluent.io/platform/current/clients/index.html)
- [Apache Avro](https://avro.apache.org/)
