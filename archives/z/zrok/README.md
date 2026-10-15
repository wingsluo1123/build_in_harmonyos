# zrok

**Display**: zrok
**Category**: network
**Homepage**: https://zrok.io/
**License**: Apache-2.0

zrok 是 openziti（NetFoundry）开发的下一代点对点安全分享平台，用于安全、私密地
共享网络与文件资源。本项目适配其主 CLI `zrok2`（模块
`github.com/openziti/zrok/v2`，go.mod 声明 go 1.26）。

## Overview

`zrok2` 同时是客户端、控制器与 agent 三合一 CLI：`share`/`access` 建立对等分享
与访问，`enable` 激活环境，`controller` 启动自托管控制器（SQLite/PostgreSQL
存储），`agent` 常驻运行，另有 `drives`（WebDAV 驱动的文件/目录同步）与
`overview`/`admin` 管理等命令。适配产物为 OHOS PC (aarch64) 上的原生
`zrok2` 可执行文件。

## Build System

- **System**: custom（Go build，绕开顶层 Makefile 的 npm UI 构建）
- **Compiler**: Go 1.26.0（go.mod 要求 >= 1.26），CGO_ENABLED=1，CC 用 OHOS
  SDK 的 `aarch64-unknown-linux-ohos-clang`
- **Module mode**: `-mod=mod` + GOPROXY (goproxy.cn)，GOTOOLCHAIN=local
- **UI**: `-tags no_zrok_ui`（上游自带 embed_stub.go 占位），headless CLI
- **Version injection**: `-ldflags -X github.com/openziti/zrok/v2/build.Version=
  v2.0.4 -X .../build.Hash=2.0.4`（对齐上游 .goreleaser）
- **签名**: 主二进制与测试 ELF 用 binary-sign-tool 自签（SHA256withECDSA）
- **Upstream tests**: `go test ./...`（12 个含 *_test.go 的包，164 项测试，
  4 项集成测试需 ZROK2_API_ENDPOINT/ZROK2_ADMIN_TOKEN 而自跳过）

## OHOS 适配要点

- zrok 依赖 `mattn/go-sqlite3`（cgo-only），必须 CGO_ENABLED=1 并配置
  `CC=aarch64-unknown-linux-ohos-clang`，产物为 ld-musl-aarch64 原生 ELF。
- Go 链接器输出与测试 ELF 放入可写 go-workspace
  （`/data/storage/el2/base/haps/entry/files/...`），规避 HMDFS mmap 限制
  （E124/E134/E166/E318）。
- 上游测试逐包 `go test -mod=mod -tags no_zrok_ui -c` 编译 → 签名 → 回源码
  目录 `-test.v -test.count=1` 运行（E318 范式）。

## Versions

| Version | Status | Date |
|---------|--------|------|
| 2.0.4 | built | 2026-10-03 |
