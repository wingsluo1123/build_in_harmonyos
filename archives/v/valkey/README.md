# valkey 8.1.4 for HarmonyOS PC

## 概述

Valkey 是 Redis 7.2 分支出来的开源（BSD-3-Clause）内存键值数据库。本目录记录
`valkey/8.1.4` 在 HarmonyOS PC（aarch64）上的适配与真机验证结果。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | valkey |
| 版本 | 8.1.4 |
| 上游仓库 | https://github.com/valkey-io/valkey |
| 下载地址 | https://github.com/valkey-io/valkey/archive/refs/tags/8.1.4.tar.gz |
| 许可证 | BSD-3-Clause |
| 构建系统 | Makefile（自带 deps/ 内联，无外部依赖） |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS PC（HongMeng Kernel）aarch64 |
| 编译器 | clang 15 / llvm-ar / llvm-ranlib |
| C 库 | musl |
| 产物签名 | binary-sign-tool 自签（未签名 ELF 不可执行） |

## 打包产物

`bin/valkey-server`、`bin/valkey-cli`、`bin/valkey-benchmark`、
`bin/valkey-sentinel`、`bin/valkey-check-rdb`、`bin/valkey-check-aof`。

## 使用

```bash
valkey-server --port 6379
valkey-cli -h 127.0.0.1 -p 6379 ping
```

## 适配要点

见 `8.1.4/notes.md`；上游测试口径与真机账本同文件。
