# termsvg 0.11.0 适配笔记

## 软件概况

- **上游**：https://github.com/MrMarble/termsvg （Go，module `github.com/mrmarble/termsvg`）
- **用途**：录制终端会话（asciicast）并导出为动画 SVG（亦支持 GIF/WebM）
- **技术形态**：**Go CLI**（`./cmd/termsvg`），go.mod 要求 go >= 1.25.6
- **许可证**：GPL-3.0-only

## 构建策略

OHOS 上 Go 的适配模式直接复用仓库内**已发布**先例 `archives/a/addchain/0.4.0`
（Go CLI，含工具链自举 + 签名 + HMDFS 规避完整解法），而非 doggo——
doggo 的归档只有 manifest+notes、**没有 conanfile.py**，未走过配方/CI 流水线，
按 W0b「历史命令在 CI 环境逐字可执行吗」不能作为 CI 可迁移性证据。

```bash
GOOS=linux GOARCH=arm64 CGO_ENABLED=0 GOTOOLCHAIN=local \
  go build -trimpath -ldflags '-s -w -X main.version=v0.11.0 ...' \
  -o <workspace>/link-out/termsvg ./cmd/termsvg
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 下载的 `go` 二进制执行报 `Permission denied` | OHOS 拒绝 exec 未签名 ELF（缺 `.codesign` 段）；真机比对证实可执行的 probe 有 `.note.ohos.ident`+`.codesign`，而 go 二进制没有 | 用 `binary-sign-tool sign -selfSign 1 -signAlg SHA256withECDSA` 为 `bin/go`、`bin/gofmt`、`pkg/tool/linux_arm64/*` 全部 ELF 签名（addchain `_sign_go_sdk_if_ohos` 同款） |
| 2 | 签名判定误跳过 `go`（伪判定为已签名） | addchain 原版用 `grep -q '.codesign'` 扫文件字节，`.` 是正则通配符，命中了 Go 二进制内的普通字符串 | 改为读真实 ELF 段：`llvm-readelf -S <bin> \| grep '\.codesign'`（本配方 `_has_ohos_signature`） |
| 3 | Go linker 在 hmdfs 上可能失败（E051/E046） | linker 对输出文件 mmap，hmdfs 不支持 | 链接输出目录放 `/data/storage/el2/base/haps/entry/files/termsvg-conan-go/<ver>/link-out`，完成后再拷回 build_folder |
| 4 | CGO 默认开启导致构建/执行权限错误 | doggo 先例记录默认 CGO 触发 `fork/exec ... permission denied` 与 go-build 缓存缺失 | `CGO_ENABLED=0` 纯静态编译 |
| 5 | `go test` 的 `*.test` 二进制无法 exec | 同 #1：未签名 ELF；测试用例 0 执行 | `go test -exec <wrapper>`，wrapper 在 exec 前对测试二进制签名 |
| 6 | 制品仓/CI 无 Go 工具链 | CI 无 go bootstrap，`go/*`、`toolchain/*` 查询均 0 条 | 配方自举 go1.26.0（多源 URL + sha256 校验） |
| 7 | GitHub 直连不稳定 | doggo/addchain 均记录 GitHub 超时 | `GOPROXY=https://goproxy.cn,...` + conandata 备用源 |

## 运行期能力核验（真机 2026-10-12）

- `termsvg --version` → `termsvg v0.11.0 (none) built on unknown`（**版本注入生效**，非上游默认 `dev`）
- `termsvg --help` → 正常列出 record/play/export 三个子命令
- `termsvg export examples/444816.cast -o out.svg` → **成功**，产出 2,449,647 字节动效 SVG（含 `<svg xmlns=...>` 与 `@keyframes`）
- `llvm-readelf -h` → ELF64 / AArch64
- 消费者测试：`--minify` 路径产出 1279 字节有效 SVG（小于全量 1343 字节）

## 验证结果

```bash
conan create archives/t/termsvg/0.11.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64
```

- 包创建成功：`termsvg/0.11.0`（`EXIT=0`）
- 上游测试：`go test -count=1 ./...` → **6 个包 ok / 0 fail**
- test_package 6 项实质断言全 PASS：
  - 二进制存在于包内
  - `--version`/`--help` 正常（版本号 v0.11.0）
  - `export` 真实 asciicast → 真实 SVG（根元素 + 命名空间 + `@keyframes` 断言）
  - `--minify` 产出更小的有效 SVG
  - aarch64 ELF 架构校验

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | Go 配方：工具链自举+签名、非 hmdfs 链接、go test 签名 wrapper、ldflags 版本注入 |
| `conandata.yml` | 官方 GitHub tag 源 + sha256 |
| `commands.json` | R38 可执行文件声明 |
| `test_package/` | R34 实质验证（真实二进制驱动 + SVG 结构断言） |
| `manifest.yaml` | status: built |

## 注意事项

- Go SDK 自举目标目录 `/data/storage/el2/base/haps/entry/files/termsvg-conan-go`（非 hmdfs），可用 `OHOS_GO_WORKDIR` 环境变量覆盖。
- 工具链签名有 `.ohos-signed` 标记文件，已签名则跳过（避免每轮重复签名）。
- 后续 Go 包（termsvg/termshot/termshark）可完全复用本配方骨架。
---

**编译结束**: 2026-10-13 04:31
**最终状态**: built
