# Adaptation Notes - unfurl 0.4.3

## Overview
unfurl is a Go CLI tool by TomNomNom that "pulls out bits of URLs provided on
stdin". It extracts URL components (scheme, user info, domain, subdomain,
root, TLD, port, path, extension, query string, fragment) and supports 8
processing modes (keys/values/keypairs/domains/paths/apexes/json/format).

- Upstream: https://github.com/tomnomnom/unfurl
- Product: `unfurl` executable (standalone CLI tool — no linkable library)
- Build system: custom (Go toolchain cross-compile)
- 类型: 【积分赛】(独立 CLI 工具)

## Source
Official GitHub archive `v0.4.3.tar.gz`:
`https://github.com/tomnomnom/unfurl/archive/refs/tags/v0.4.3.tar.gz`

sha256 (实测, 8102 bytes):
`124e7c476af31745838322422771c664280d192aa56b586e431fc0b9b422ea50`

## Conan Recipe (0.4.3)
- Conan 2.x recipe, `package_type = "application"`, `no_copy_source = True`.
- `build()`: `go build -trimpath -ldflags '-s -w' -o unfurl .`,
  OHOS 平台设置 `GOOS=ohos GOARCH=arm64 CGO_ENABLED=0`。
- `package()`: 二进制复制到 `bin/unfurl`, LICENSE 复制到 `licenses/`。
- `package_info`: `cpp_info.libs=[]` (无链接库), `bindirs=["bin"]`。
- 无补丁: 纯 Go 源码, 无需 C/C++ 适配。

## OHOS Adaptation
unfurl 是纯 Go 程序, 无 CGO 依赖。Go 1.22+ 原生支持 `GOOS=ohos`,
`GOARCH=arm64` 直接交叉编译出 HarmonyOS aarch64 可执行文件。
依赖模块 (Cgboal/DomainParser, jakewarren/tldomains) 由 `go build` 自动拉取,
无需额外配置。

## Dependencies
- 构建期: 无 (Go modules 由 go build 管理, CGO_ENABLED=0)。
- 运行时: 无 (标准输入/输出过滤工具)。

## Verification
- conandata.yml sha256 与 v0.4.3.tar.gz 实测值一致
  (`124e7c47...`)。
- 上游测试: `format_test.go` 的 `TestFormat` 含 32 个 case,
  通过 `go test ./...` 验证。
- test_package 校验包内 `bin/unfurl` 存在且可执行,
  并实际运行 `echo 'https://example.com/foo?a=b' | unfurl -u` 验证输出。

---

**编译结束**: 2026-07-31
**最终状态**: built
