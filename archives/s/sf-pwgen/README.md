# sf-pwgen

`sf-pwgen` 上游是 macOS 专属的命令行口令生成器（Anders Bergh，`anders/pwgen`），1.5 版经 SecurityFoundation 口令助手 API 生成口令，构建需 `-framework Foundation -framework CoreFoundation -framework SecurityFoundation`，只能在 Apple 平台编译。

本目录收录其 HarmonyOS PC 可移植实现（1.5）：补丁新增的 `sf-pwgen-portable.c` 用纯 C99 复刻了全部 CLI 契约（`-a/-c/-l/-L/-v/-h`、五种算法、默认值 count 5 / length 12、长度钳制 8..128、1.5 的偏短警告、`sf-pwgen 1.5` 版本串），熵源为 `/dev/urandom`（拒绝采样去模偏），零第三方依赖，产物为 `bin/sf-pwgen`。

## 功能概述

- `-a memorable|random|letters|alphanumeric|numbers`（默认 memorable）
- `-c N` 生成 N 个口令（默认 5，小于 1 按 1 处理）
- `-l N` 期望长度（默认 12，钳制到 8..128；memorable 为词拼接，超长请求会触发偏短警告，与上游 1.5 行为一致）
- `-L en|de|es|fr|it|nl|pt|jp` 语言（可移植后端内建英文词表，其他合法语言为 CLI 兼容接受；非法语言打印 warning）
- `-v` 打印 `sf-pwgen 1.5`；`-h` 打印用法

## 依赖关系

- 编译依赖：无（仅 libc + `/dev/urandom`；musl 全部提供）
- 运行依赖：无第三方库

## OHOS 适配要点

- 上游 `sf-pwgen.m` 无法在 OHOS 编译是平台事实而非配置问题，不做宏开关式的修补；改为新增可移植后端文件，macOS 原文件原样保留
- 补丁与配方均不含 `__OHOS__` 平台宏（R8/PF5），可移植后端对 Linux 同样可用
- 上游仅有空占位 XCTest，无有效测试；`test_package` 补全功能覆盖与鸿蒙产物检查

## 参考资料

- 上游仓库：<https://github.com/anders/pwgen>
- 上游版本历史：`VERSIONS.md`（1.5 2019-04-13：偏短警告 + Travis 修复）
