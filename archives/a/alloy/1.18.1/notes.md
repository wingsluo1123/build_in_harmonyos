# alloy 1.18.1 HarmonyOS PC notes

## 软件简介
Grafana Alloy — OpenTelemetry Collector 分发版，内置 Prometheus 管道，
支持 metrics/logs/traces/profiles。上游 https://github.com/grafana/alloy
（Apache-2.0）。主程序为 otel collector builder 生成的独立模块
`collector/`（`module github.com/grafana/alloy/otel_engine`），需在
`collector/` 内 `go build`；根 `go.mod` 以 `replace` 引用根模块与
`syntax` 子模块。

## 构建策略（本地实测）
- 纯 Go 静态构建：`GOOS=linux GOARCH=arm64 CGO_ENABLED=0`（与 murex 一致）
- Go 工具链 go1.26.5（go.mod 要求），配方 conandata 声明 aliyun 镜像 + 官方 sha256
- **本地构建成功**：`go build -trimpath -ldflags "-s -w"` 产出 linux/arm64
  静态二进制（417MB，含全部 otel-collector 组件）
- 输出与缓存放 hmfs 工作根（/data/storage/el2/base/cache），避免
  `link: mapping output file failed: permission denied`（HMDFS mmap 限制）
- 构建后用 binary-sign-tool 签名（OHOS 执行策略要求）

## 关键适配发现
1. **二进制签名**：OHOS 要求可执行文件签名（`binary-sign-tool sign -selfSign 1`），
   未签名 Go 产物 execve 报 EACCES；clang 编译产物不受限（本地实测）。
2. **Go 工具链需签名**：go 及其子工具（go/pkg/tool/linux_arm64/*）均为
   Go 产物，需逐个签名后才能执行。
3. **HMDFS 链接限制**：链接器输出到 /storage 报 permission denied，
   需放到工作根再拷回。
4. **运行限制**：alloy 启动时 cilium/ebpf rlimit 检测调用 bpf 系统调用
   （arm64 syscall 280），本机 seccomp 拦截 → SIGSYS（--version 亦如此）。
   运行验证需官方 CI/目标设备完成（同 murex 先例：本地结构验证 + CI 运行验证）。

## 测试
- 上游：Go 测试套件（`go test ./...`，根模块 + collector 模块），
  配方 build() 内置（OHOS 下经 -exec 签名包装器执行）
- test_package：消费者 smoke test（--version 版本断言 + alloy fmt 配置解析）

## 本地验证状态
- go build：通过（本地构建产物 alloy-bin 417MB，已签名）
- conan create：本地执行（配方结构 + 构建流程，见任务记录）
- 二进制运行：本机 seccomp 拦截 bpf → SIGSYS，需目标设备/CI 验证
