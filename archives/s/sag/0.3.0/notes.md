# sag 0.3.0 — 适配笔记

> 档案创建时间: 2026-10-13
> 最后更新: 2026-10-13
> 状态: built
> 适配路径: 路径 A（基础适配）

## 一、基本信息
| 项目 | 值 |
|------|-----|
| 软件 | sag |
| 版本 | 0.3.0 |
| 上游仓库 | https://github.com/steipete/sag |
| 构建系统 | Go modules (custom) |
| 许可证 | MIT |
| 源码 | https://github.com/steipete/sag/archive/refs/tags/v0.3.0.tar.gz |
| SHA256 | acb6f2d626ce47640dc71c927dae27c6c104bab727dfa4f5bb14ebea80c11a63 |
| Go 版本 | 1.25.0 |

## 二、适配要点

### Go 工具链自举
- OHOS 真机未预装 Go，配方在 build 前通过 `_ensure_go_toolchain()` 自动下载官方 Go 1.25.0 二进制包
- 支持 arm64 / amd64 双架构，优先使用 `golang.google.cn` 镜像，回退 `mirrors.aliyun.com` 与 `dl.google.com`
- 下载后对 `go`, `gofmt` 及 `pkg/tool/linux_*/*` 下全部 ELF 用 `binary-sign-tool` 签名
- go.mod 要求 go >= 1.25.0，因此自举版本必须为 1.25.0（低于此版本会因 go.mod 约束拒绝构建）
- 2026-10-13 真机 compile 失败 `tar (grandchild): gzip: Cannot exec: Operation not permitted`：系统 `tar -zxf` 需 fork/exec 外部 `gzip`，在 OHOS 受限环境被拒；`_ensure_go_toolchain()` 改用纯 Python `urllib + hashlib + tarfile` 下载解压（`_download_and_extract_go_sdk`，沿用 gadap/qalculate-gtk 的 cmd-pkgs 纯 Python 解压先例），不调用系统 tar/gzip，逐镜像重试并校验 gzip 魔数与 SHA256，解压失败清理后换镜像

### HMDFS 规避
- Go linker 的最终输出不能落在 HMDFS，链接阶段输出到 `$OHOS_GO_WORKDIR/link-out`
- `TMPDIR` / `GOTMPDIR` / `GOCACHE` / `GOMODCACHE` 全部重定向到非 HMDFS 工作区

### oto CGO-free 修复（2026-10-13 真机 compile 失败）
- 真机 `CGO_ENABLED=0 + GOOS=linux` 下 `oto v3.4.0` 编译失败：`context.go:38:11: undefined: context` / `:100:21: undefined: newContext`（与 ebitengine/oto#260、Linux ARM64 同错；v3.4.0 的 Linux 后端是 CGO ALSA，无 CGO 时无 `newContext` 定义）
- 修复：`build()` 先执行 `go get github.com/ebitengine/oto/v3@v3.5.1 + go mod tidy`（`_oto_version`），v3.5.0+ 自带 pure-Go PulseAudio 后端与无 CGO ALSA 回退，`CGO_ENABLED=0` 可直接编译；sag 使用的 oto 公共 API（NewContext/NewPlayer）前后兼容（v3.5 仅新增 `ApplicationName` 可选字段）
- 不启用 CGO 交叉工具链、不引入 ALSA 系统依赖

### 上游测试
- 上游测试命令：`go test -v -count=1 ./...`（CI 的 `go test ./...`，另需 `libasound2-dev` 的音频依赖仅影响运行时播放，不影响单测）
- OHOS 上测试 ELF 需签名后才能执行，通过 `go test -exec ohos-test-exec.sh` wrapper 在执行前自动签名
- `-race` 需要 CGO，在 `CGO_ENABLED=0` 下自动回退到不带 `-race` 的 `go test -v -count=1 ./...`
- 测试统计：顶层 `Test*` 共 74 个函数，分布在 4 个包（cmd / cmd/sag / internal/audio / internal/elevenlabs），Go mock httptest 覆盖 elevenlabs 客户端
- 详见 `test_package/MANIFEST.yml` 声明

### 版本注入
- 上游 cobra `Version: "0.3.0"` 硬编码在 `cmd/root.go`，无需 ldflags 注入
- `sag -V` 输出 `sag 0.3.0`，与上游发布一致

## 三、源码修改清单
| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|---------|
| (无) | Go 源码在 OHOS 上可直接编译，无需补丁 | - | 无补丁 |

## 四、编译命令
```bash
# 探索性编译（复现 conan 流程）
go mod download
go build -trimpath -ldflags "-s -w" -o bin/sag ./cmd/sag
go test -v -count=1 ./...

# Conan 验证
conan create archives/s/sag/0.3.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 五、验证
- 本地需在 HarmonyOS aarch64 真机预检通过后合入
- `sag -V` / `sag --help` / `sag prompting` 均可离线执行
- `sag speak` / `sag voices` 需要 ElevenLabs API key，仅在 test_package 做 help 级验证，不做真实网络调用

## 六、已知限制
- 音频播放（oto/afplay）在 headless 真机仅做坏 MP3 解码单测，不做真实扬声器播放
- `GOTOOLCHAIN=local` 强制使用自举 Go 1.25.0，避免自动下载更新版本

## 七、结束记录
- 最终状态: built
- 结束时间: 2026-10-13
