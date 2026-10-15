# zrok 2.0.4 适配笔记

## 基本信息

- **软件**: zrok — openziti 的下一代点对点安全分享平台（主 CLI `zrok2`）
- **版本**: 2.0.4（首次适配，无后缀）
- **上游**: https://github.com/openziti/zrok（tag v2.0.4）
- **许可证**: Apache-2.0（LICENSE 为 Apache License 2.0 全文）
- **构建系统**: Go custom（顶层 Makefile 的 `.DEFAULT_GOAL=build` 先 npm 构建
  ui/ 与 agent/agentUi/ 再 `go install ./cmd/zrok2`；本适配直接 `go build
  ./cmd/zrok2` 绕开 npm）
- **Go 要求**: go.mod 声明 `go 1.26`，配方自举 Go 1.26.0 工具链
  （`GOTOOLCHAIN=local`）
- **源码**: `https://github.com/openziti/zrok/archive/refs/tags/v2.0.4.tar.gz`
- **SHA256**: `07c98d5f9be96885ec98b40446d4d8867f19f4b59f3ae4de0b41cdac8db6c392`
  （实测下载验算一致）
- **申请人**: GoliWie（编译协作者子任务，主编审核后提交 PR）

## 语言预检（R47）误判说明

`lang-preflight` 因检测器缺陷把 zrok 判为 `mixed`：sdk/python 辅助目录里的
`pyproject.toml` 遮蔽了顶层 `go.mod`，触发源码统计的 Python 分支。按 R47
边界规则「辅助脚本不算主体」：zrok 主体 79% 是 Go、顶层有 go.mod、模块名
`github.com/openziti/zrok/v2`，本包按 Go 适配。制品仓已有 kubeaudit 0.22.2、
argo 4.0.5 两个 Go 包成功先例，流程通吃。检测器误判已在 notes 记录，供后续
修复检测器参考（非本包问题）。

## 上游测试审计（2026-10-03，基于 v2.0.4 源码包实测）

顶层 Makefile `test` 目标为 `go test ./... -count=1` + `go vet ./...`。
`go test ./...` 覆盖 63 个包，其中 **12 个包含 *_test.go（35 个文件）**：

| 包 | 文件数 | 说明 |
|----|--------|------|
| cmd/zrok2 | 1 | access/delete/unaccess 请求解析辅助（deleteAccess_test.go） |
| controller | 2 | share name 生命周期、unaccess 处理 |
| controller/automation | 1 | ziti automation 客户端接口契约 |
| controller/limits | 9 | limit 类/带宽/资源计数/用户限额（agent/bandwidthClass/config/influxReader/limitAction/relaxAction/resourceCountClass/userLimits/warningAction） |
| controller/store | 4 | store 模型序列化（account/bandwidthLimitJournal/environment/frontend） |
| drives/davServer | 6 | WebDAV file/if/lock/prop/xml/webdav 处理器 |
| drives/davServer/internal/xml | 5 | WebDAV 用 XML 编解码（atom/example/marshal/read/xml） |
| drives/sync | 1 | drive sync 安全（路径穿越防护） |
| endpoints | 1 | OAuth cookie 序列化 |
| endpoints/proxyUi | 1 | interstitial/template 渲染 |
| sdk/golang/sdk | 3 | SDK config/model 单测 + 4 个集成测试 |
| util | 1 | duration 解析 |

- `sdk/golang/sdk/integration_test.go` 的 4 个集成测试
  （TestIntegrationEnableDisable/ShareLifecycle/AccessLifecycle/Overview）在
  未设置 `ZROK2_API_ENDPOINT` / `ZROK2_ADMIN_TOKEN` 时按上游语义
  `t.Skip("... not set — skipping integration tests")` **自跳过**，无需真实
  zrok 控制器/网络。
- 全部 12 个包在 build() 内按 E318/P017 范式执行：`go test -mod=mod -tags
  no_zrok_ui -c` 编译到 go-workspace/test-out、binary-sign-tool 自签名后回包
  源码目录 `-test.v -test.count=1` 运行（保留相对 fixture 路径）。

## 编译方案

```bash
CGO_ENABLED=1 GOOS=linux GOARCH=arm64 GOTOOLCHAIN=local GOFLAGS=-mod=mod \
GOPROXY=https://goproxy.cn,direct GOSUMDB=sum.golang.google.cn \
CC=aarch64-unknown-linux-ohos-clang \
  go build -trimpath -mod=mod -tags no_zrok_ui \
  -ldflags "-s -w \
    -X github.com/openziti/zrok/v2/build.Version=v2.0.4 \
    -X github.com/openziti/zrok/v2/build.Hash=2.0.4" \
  -o zrok2 ./cmd/zrok2
```

### 关键决策与 kubeaudit/argo 的 delta（⭐ 最重要）

1. **CGO_ENABLED=1 而非 0**：zrok 依赖 `github.com/mattn/go-sqlite3`，
   该包全部文件带 `//go:build cgo`（sqlite3.go/error.go 均 import "C"），
   CGO_ENABLED=0 时包退化为空，`controller/createFrontend.go` 的
   `sqlite3.Error{}`/`sqlite3.ErrConstraint` 报 `undefined: sqlite3.Error`。
   上游 .goreleaser-linux-arm64.yml 本就 `CGO_ENABLED=1 +
   CC=aarch64-linux-gnu-gcc`。OHOS 上改用 HarmonyOS SDK 自带的
   `aarch64-unknown-linux-ohos-clang`（profile PATH
   `/data/service/hnp/bin` 内），产物为 `ld-musl-aarch64.so.1` 动态链接的
   OHOS 原生 ELF。cgo 需的 lld 依赖 libxml2.so.16，需把 llvm/lib 加入
   LD_LIBRARY_PATH（配方 `_add_llvm_libpath`）。
2. **UI 用上游自带 `-tags no_zrok_ui`**：ui/ 与 agent/agentUi/ 的 embed.go
   带 `//go:build !no_zrok_ui`，上游同时提供 embed_stub.go（空 embed.FS），
   打该 tag 即跳过 npm 构建，**无需造 UI placeholder**（与 argo 造
   ui/dist/app/index.html 不同）。其余 embed（endpointUi/index.gohtml、
   controller/emailUi/*.gohtml、store/sql/**/*.sql、proxyUi/*.html）文件均在
   源码包内。
3. **版本注入**：对齐 .goreleaser 的 `-X .../build.Version={{.Tag}}` 注入
   v2.0.4；`zrok2 version` 输出 ASCII banner + `v2.0.4 [2.0.4]`。
4. **Go 工具链自举**：无系统 go；配方 `_ensure_go_toolchain` 从
   dl.google.com 下载 go1.26.0.linux-arm64.tar.gz（sha256
   bd03b743…75704cd，已由 dl.google.com 官方 .sha256 文件核验），解压到
   go-workspace/go-sdk，并把 go/gofmt/pkg/tool 下所有 ELF 用 binary-sign-tool
   自签后才能 execve（OHOS 对未签名 ELF 拒绝执行）。
5. **go-workspace 路由**：GOCACHE/GOMODCACHE/GOTMPDIR/link-out/test-out 全部
   放 `/data/storage/el2/base/haps/entry/files/zrok-conan-go/2.0.4`
   （`OHOS_GO_WORKDIR` 可覆盖）。`go build -o` 在 HMDFS/tmpfs 上 mmap 输出
   文件报 `mapping output file failed: permission denied`（E124/E134/E166），
   ext2 分区可写可执行。
6. **无 vendor/**：构建期先 `go mod download`（GOPROXY=goproxy.cn）拉取模块
   闭包（go.mod 直接依赖 ~40 个、间接闭包约 60 个，go.sum 约 1700 行）。
7. **测试**：逐包 `go test -c` → 签名 → 回源码目录 `-test.v -test.count=1`
   运行并统计 HMBS_GO_TEST_PKG / HMBS_UPSTREAM_TEST_RESULT。

## test_package（OHOS 特有用例，非上游复用）

1. `version` 输出含 `v2.0.4`（验证 -X 注入在 OHOS 工具链下生效）
2. `--help` 退出码 0 且列出 share/controller 等命令（cobra 正常）
3. `completion bash` 生成合法 bash 补全脚本
4. 未知子命令退出码非 0（CLI 错误处理）
5. （OHOS-only）产物 ELF 含 binary-sign-tool 写入的 `.codesign`/`.note.ohos`
   签名节（未签名 ELF 会被 HarmonyOS execve 拒绝）
6. （OHOS-only）产物含 `ld-musl-aarch64`（OHOS 原生 musl ABI，无 glibc 耦合）

## 源码修改

无源码修改，无 patches，纯 Go 编译（conandata.yml patches: {}）。

## 依赖闭包说明

- **Conan 层**: conanfile.py 无 `requires`/`tool_requires` —— zrok 无 C 库
  依赖，Go 模块闭包全部经 GOPROXY 在 build() 内拉取，不经过 conan 制品仓
  （W0 依赖检查天然通过，见 reports/W0-report.md）。
- **Go 模块层**: 直接依赖含 caddy/v2（+greenpau/caddy-security）、
  go-openapi 全家、openziti/channel、charmbracelet/bubbletea（TUI）、
  influxdb-client-go、go-sqlite3（cgo）、lib/pq 等；间接闭包含
  golang.org/x/...、google.golang.org/grpc、k8s.io、modernc?（无）、
  go.step.sm/crypto 等，共约 60 个模块。全部可从 goproxy.cn 拉取。
- **运行时**: `zrok2` 客户端命令离线可用（version/help/config/enable 等）；
  share/access 需要可用的 zrok 控制器与网络（运行环境条件）；controller
  子命令需要 SQLite（cgo 已内嵌）或 PostgreSQL（需外部服务）。

## 验证结果（2026-10-03 真机回填）

- `go test -mod=mod -tags no_zrok_ui`（12 包离线口径，`go test -c` 编译 →
  binary-sign-tool 签名 → 回源码目录 `-test.v -test.count=1` 运行）：
  **discovered=executed=164，passed=160，failed=0，skipped=4**
  （4 项跳过为 sdk/golang/sdk 集成测试，需 ZROK2_API_ENDPOINT/ZROK2_ADMIN_TOKEN
  真实控制器，按上游语义自跳过）。
- 逐包通过数（HMBS_GO_TEST_PKG）：cmd/zrok2 5 / controller 9 /
  controller/automation 3 / controller/limits 27 / controller/store 9 /
  drives/davServer 34 / drives/davServer/internal/xml 53 / drives/sync 6 /
  endpoints 7 / endpoints/proxyUi 2 / sdk/golang/sdk 4（另 SKIP 4）/
  util 1 —— 全部 0 fail。
- test_package 6/6 通过（--ohos 口径：version 嵌入 / help / completion /
  未知命令错误处理 / OHOS 签名节 / musl ABI），`HMBS_TEST_PACKAGE_RESULT`
  passed。
- 主二进制 `zrok2`（约 84 MiB，ELF arm64 dynamic musl，stripped，已签名）：
  `zrok2 version` → `v2.0.4 [2.0.4]`；`zrok2 --help` 列出全部子命令。
- 权威 CI：`zsh ci/conan/build_and_test.sh`，CI_PACKAGES=archives/z/zrok/2.0.4，
  CI_BRANCH=feat/zrok-2.0.4（由主编/CI 触发）。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 2.x Go 配方（自举 go1.26.0、CGO_ENABLED=1 + OHOS clang、go-workspace 路由、签名、上游测试） |
| conandata.yml | 官方源 + sha256（07c98d5f…6c392）+ patches: {} |
| test_package/ | conanfile.py + test.sh + MANIFEST.yml（6 断言，实际执行被测二进制） |
| commands.json | CLI 工具声明（软件级，R38） |
| manifest.yaml ×2 | 软件级 + 版本级（status: built） |
| reports/test-report.md | 上游测试详情 |
| reports/W0-report.md | 依赖发布检查（无 conan 依赖，天然通过） |

## 注意事项

- 版本号策略：首次适配用上游版本 2.0.4，无后缀；若后续修复适配问题按
  R37 递增为 2.0.4.1。
- 上游 Makefile 的 `build` 目标含 npm UI 构建，本适配用 `-tags no_zrok_ui`
  headless 构建；如需 UI 需在 OHOS 上跑 npm build（node/npm v24 可用，但
  Vite 产物未验证，不作为本包交付范围）。
- `zrok2 controller` 的 SQLite 路径依赖 cgo 内嵌 sqlite3，本适配已启用 cgo
  故可用；PostgreSQL 路径需外部 postgres 服务。
- 编译/测试 ELF 均须在签名后运行；go-sdk 内的工具二进制（link/compile 等）
  也须先签名，配方 `_sign_go_sdk_if_ohos` 统一处理并写 `.ohos-signed` 标记。
---

**编译结束**: 2026-10-03 13:58
**最终状态**: built
