# yutu

`yutu` 是面向 YouTube 的 AI 工具集：一个命令行程序、一个 MCP 服务器，也是一个
自动化 YouTube 工作流的 Agent（上传/优化视频、管理评论、播放列表、频道品牌等）。

- 上游：https://github.com/eat-pray-ai/yutu
- 许可：Apache-2.0
- 首页：https://yutu.ifor.dev

## 上游形态

| 项 | 值 |
|---|---|
| 语言 | Go（纯 Go，无 CGo） |
| 模块 | `github.com/eat-pray-ai/yutu`（入口 `main.go` 在仓库根目录） |
| go 指令 | `go 1.26.0` |
| 构建 | `CGO_ENABLED=0 go build -trimpath -tags netgo -ldflags "-s -w -X .../cmd.Version=..."` |
| 分发 | GitHub Releases / npm `@eat-pray-ai/yutu` / Docker（`FROM scratch`）/ `go install` |

## OHOS 适配要点

1. **零第三方库依赖**：上游以 `CGO_ENABLED=0` + `-tags=netgo` 构建，DNS/TLS 走纯 Go
   实现，产物是完全静态的 ELF；上游 `Dockerfile` 用 `FROM scratch` 只额外拷入
   `ca-certificates.crt`，可作旁证。
2. **Go 工具链内联下载**：OHOS 镜像不含 Go。按知识 `E250`
   （`rec_approach: download-go-sdk`，`rec_impl: inline-build-method`）在 `build()`
   内从权威镜像下载 Go SDK，不声明 conan `requires()`（与仓内 57 个 Go 配方一致）。
3. **链接 mmap 规避**：Go 链接器需要 mmap 输出文件，HMDFS 上会
   `mapping output file failed: permission denied`（E051/E046）；链接输出改写到
   `/data/storage/el2/base/haps/entry/files` 下的可写工作区。
4. **ELF 签名**：OHOS 拒绝 `execve` 未带 `.codesign` 的 ELF（E128）。产出的 `yutu`
   与 Go SDK 的 `pkg/tool/linux_arm64/*` 工具二进制都由 `binary-sign-tool` 自签名。
5. **上游测试**：30 个 `*_test.go`（177 个顶层 Test 函数）。OHOS 上不能直接
   `go test ./...`（测试二进制未签名不可执行），改为逐包 `go test -c` →
   签名 → 执行测试二进制，统计与日志见 `0.10.9/reports/`。

## 目录

```
yutu/
├── README.md
├── commands.json          # R38：软件级 CLI 声明
├── manifest.yaml          # 软件级元数据
└── 0.10.9/
    ├── conanfile.py
    ├── conandata.yml
    ├── manifest.yaml
    ├── notes.md
    ├── reports/
    └── test_package/
```
