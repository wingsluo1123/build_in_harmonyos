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
- Conan 2.x recipe, `package_type = "application"`, `no_copy_source = True`。
- `build()`: 先跑上游单测 `go test ./...`，再
  `go build -trimpath -ldflags "-s -w" -o <build_folder>/unfurl .`，
  环境为 `GOOS=linux GOARCH=arm64 CGO_ENABLED=0`。
- `package()`: 二进制复制到 `bin/unfurl`, LICENSE 复制到 `licenses/`。
- `package_info`: `cpp_info.libs=[]` (无链接库), `bindirs=["bin"]`。
- 软件级 `commands.json`（R38）声明该包为 tool。
- 无补丁: 纯 Go 源码, 无需 C/C++ 适配。

## OHOS Adaptation
unfurl 是纯 Go 程序, 无 CGO 依赖。

**关键更正**：标准 Go 工具链**没有** `ohos` 这个 GOOS 目标，
`GOOS=ohos` 会直接报 `unsupported GOOS/GOARCH pair ohos/arm64`。
HarmonyOS 基于 Linux 内核，正确做法是
`CGO_ENABLED=0 GOOS=linux GOARCH=arm64` 生成静态 ELF。

这不是推测：本仓库 `archives/` 下共 **51 个包的 notes.md 记录了 `GOOS=linux`**，
其中 34 个明确配 `CGO_ENABLED=0`，**没有任何一个包使用 `GOOS=ohos`**。
参考 `archives/a/amass/4.2.0/notes.md`，其构建命令与本配方逐字一致：

```
GOPROXY=https://goproxy.cn,direct CGO_ENABLED=0 GOOS=linux GOARCH=arm64 \
  go build -trimpath -ldflags="-s -w" -o amass ./cmd/amass/
```

`archives/b/buildifier/8.0.3/notes.md` 亦记录 `GOROOT=~/usr/local/go1263`
与同一组环境变量。

其余环境要点：

- Go 版本：必须用 1.26.3（`~/usr/local/go1263`）；1.26.0 的 HarmonyOS 二进制
  存在 corrupted 问题。`go` 未必在 profile 的 PATH 中，配方会自行探测。
- 构建目录：`basic_layout` + `no_copy_source = True` 会把 `source_folder` 与
  `build_folder` 分开，而 `go.mod` 在 `source_folder`，因此 `build()` 内必须
  `with chdir(self, self.source_folder):`，否则报 `no Go files in ...`。
- 环境注入：`self.run(env=...)` 的 `env` 形参接收的是**环境脚本名**（str/list），
  传 `dict(os.environ)` 会抛 TypeError；应使用 `conan.tools.env.Environment`。
- 依赖模块：上游 `go.mod`（`go 1.18`）声明
  `github.com/Cgboal/DomainParser`、`github.com/jakewarren/tldomains`，
  以及 indirect 的 `golang.org/x/net`。三者由 `go build` 自动拉取，
  需 `GOPROXY=https://goproxy.cn,direct` 规避 proxy.golang.org 不可达。
- 不设 `GOFLAGS=-mod=mod`：上游 `go.sum` 完整，默认 `readonly` 即可；且
  `no_copy_source=True` 下 `source_folder` 是共享源码缓存，应避免写入。

## Dependencies
- 构建期: 无 (Go modules 由 go build 管理, CGO_ENABLED=0)。
- 运行时: 无 (标准输入/输出过滤工具)。

## Verification
- conandata.yml sha256 与 v0.4.3.tar.gz 实测值一致
  (`124e7c47...`)。
- 上游测试: `format_test.go` 的 `TestFormat` 含 32 个 case（覆盖
  `%d %p %q %f %e %u %a %S %r %t %@ %: %? %# %P` 共 15 个格式动词），
  已在 `build()` 中通过 `go test ./...` 真实执行。
- test_package 无条件校验包内 `bin/unfurl` 存在且具可执行位，
  再由 `test.sh` 以上游 README 官方示例为输入，逐条断言
  `domains` / `--unique` 去重 / `apexes` / `paths` / `keys` / `values`
  六种模式的实际输出。

  注意：unfurl 遇到未知 mode 时只向 stderr 打印 `unknown mode` 便 `return`，
  **退出码仍为 0**（见上游 `main.go`）。所以"命令能跑通"证明不了功能正确，
  必须比对 stdout 内容，否则就是恒真的假阳性测试。

---

**编译结束**: 2026-07-31
**最终状态**: built
