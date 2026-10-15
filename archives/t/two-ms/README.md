# two-ms 5.2.4 — OpenHarmony 编译记录

## 基本信息
- 软件: two-ms（Checkmarx/2ms 的 Homebrew formula 名，交付命令 `2ms`）
- 版本: 5.2.4（Go module `github.com/checkmarx/2ms/v5`，tag `v5.2.4`）
- 上游: https://github.com/Checkmarx/2ms （Apache-2.0）
- 构建系统: go（`go build`）
- 目标: ohos-aarch64
- 依赖: 无第三方 C/C++ 库（N=0；仅 Go module，由 GOPROXY 自动拉取）

## 编译指导
- OHOS 原生环境无 Go 工具链（E250）：配方在 `build()` 内自举下载 Go 官方 SDK
  （`conandata.yml` 的 `go_toolchain`，go1.26.9，三镜像 + sha256）
- 纯 Go 静态构建：`CGO_ENABLED=0 GOOS=linux GOARCH=arm64`
  ```bash
  go build -trimpath \
    -ldflags "-s -w -X github.com/checkmarx/2ms/v5/cmd.Version=5.2.4" \
    -o 2ms .
  ```
- 版本串由 `-X .../v5/cmd.Version` 注入；上游 `release.yml` 写的是缺 `/v5` 的符号路径，
  对 v5 module 无效，本配方用正确路径
- 工作区/缓存/链接输出放 ext2 分区（E166 HMDFS/SELinux 限制 Go link；E046 无 getcwd）
- 自举 SDK 与交付 ELF 用 `binary-sign-tool` 自签名（E128：鸿蒙 execve 需 `.codesign` 段）

## 补丁清单
- 无。源码零改动。

## 测试
- 上游测试在 `build()` 内真跑：`go test -count=1 -json -timeout 900s ./...`
  （OHOS 上加 `-exec` 签名 wrapper，E318）
- 结果：**1139 用例，通过 1137，失败 0，跳过 2**（跳过为上游自身 `t.Skip`）
- 消费者测试 `test_package/consumer_check.py`：31 项断言全通过，含鸿蒙特有用例 H1

## 已知限制
- 运行期扫描 Git 仓库时调用系统 `git`（上游运行镜像含 git 2.53.0）；`git` 为系统工具，
  非第三方库，未随包交付。
- 上游 `make test` 使用 `-race`（需 cgo），与 `CGO_ENABLED=0` 静态构建口径冲突；
  本包按上游 CI（`pr-validation.yml` / `release.yml`）实际的 `go test ./...` 执行。
