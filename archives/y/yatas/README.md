# yatas

A simple tool to audit AWS/GCP infrastructure for misconfiguration or potential security issues with plugins integration — 纯 Go 编写的命令行工具。

## 概述

yatas 通过插件集成审计 AWS/GCP 基础设施的配置错误与潜在安全问题。CLI 支持 `--init`（生成示例 `.yatas.yml` 配置）、`--readme`（生成 README checks）、`--install`（安装插件）、`--ci`（CI 退出码）、`--compare`（与上次报告对比）、`--hds`（仅运行 HDS 检查）等。

## 已编译版本

- **1.6.1** (2025-12-12) — Go 1.26.5, CGO_ENABLED=0, static build

## 关键信息

- **源码**: https://github.com/padok-team/yatas
- **构建系统**: Go (custom，根包 `go build .`，main.go 在仓库根目录)
- **依赖**: Go ≥ 1.20
- **平台**: linux/arm64 (HarmonyOS/OpenHarmony)

## 鸿蒙适配要点

1. 纯 Go 静态编译：CGO_ENABLED=0、GOOS=linux、GOARCH=arm64，无 cgo 依赖
2. Go linker mmap 在 HMDFS 上失败 → 链接输出放到 ext2 可写分区（`/data/storage/el2/base/haps/entry/files`）
3. OHOS 上每个被 fork/exec 的 ELF 必须用 binary-sign-tool 自签名（含 `.codesign` section），Go SDK 工具链同样需要签名
4. 上游 1.6.1 自带 11 个 `*_test.go`、48 个纯本地 Go 单元测试；`go test -v -count=1 ./...` 全量运行

## 依赖关系

- **编译依赖**: Go 1.26.5 SDK（本地未找到时自动下载）
- **运行依赖**: 无（静态二进制，仅依赖 libc 内核接口）

## 参考资料

- **官网**: https://github.com/padok-team/YATAS
- **源码仓库**: https://github.com/padok-team/yatas
