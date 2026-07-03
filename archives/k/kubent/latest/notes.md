# kubent latest 适配笔记

## 编译环境
- 构建系统: Go (go build via Makefile)
- 编译日期: 2026-07-03
- 编译器: clang/clang++ (C/C++ fallback), Go 1.26.4 linux/arm64
- 状态: published

## 编译步骤

kubent (Kube No Trouble) 是一个 Go 项目，使用 Go modules 管理依赖。

1. 源码来自 GitHub: https://github.com/doitintl/kube-no-trouble (tag 0.7.3)
2. 设置 Go 环境变量（CI 必需）:
   ```bash
   export GOPROXY=https://goproxy.cn,direct
   export GOSUMDB=off
   export GONOSUMDB=*
   export GOFLAGS=-mod=mod
   ```
3. 下载依赖: `go mod download`
4. 编译: `make build` (内部调用 `go build -ldflags="-s -w" -o bin/kubent-linux-arm64 ./cmd/kubent`)
5. 安装到 staging: `cp bin/kubent-linux-arm64 $TEST_PREFIX/bin/kubent`
6. 测试: `go test -v -timeout 120s ./...`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | HarmonyOS 环境缺少 CA 证书 | 使用 `curl -k` 手动下载 tarball，然后用 `--no-download` 模式 |
| 2 | Go 模块下载失败 | proxy.golang.org 和 sum.golang.org 在 CI 环境不可达 | 设置 GOPROXY=https://goproxy.cn,direct, GOSUMDB=off, GONOSUMDB=* |
| 3 | 编译耗时长 (~9分钟) | kubent 依赖 k8s client-go, helm v3, opa 等大型库 | 正常现象，无需特殊处理 |
| 4 | 构建系统误识别为 autotools | init-build 的 _guess_build_system 基于 URL 猜测 | 手动重写 conanfile.py 为 Go 构建系统 |

## 源码修改

无源码修改，kubent 在 HarmonyOS/OpenHarmony 平台上开箱即用。

## 依赖版本

- Go 1.26.4 (linux/arm64)
- 无外部编译依赖 (Go 静态编译, CGO_ENABLED=0)
- Go 模块依赖通过 goproxy.cn 自动下载

## 验证结果

```bash
$ ./bin/kubent-linux-arm64 --version
INF version dev (git sha dev)

$ file bin/kubent-linux-arm64
ELF executable, 64-bit LSB arm64, static, stripped

$ go test -v ./...
--- PASS: TestRego125 (0.23s)
--- PASS: TestRego126 (0.08s)
--- PASS: TestRego127 (0.02s)
--- PASS: TestRego129 (0.06s)
--- PASS: TestRego132 (0.09s)
--- PASS: TestRegoCustom (0.03s)
--- PASS: TestRegoFuture (0.10s)
PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/kubent-linux-arm64 | ~40MB | 静态 ELF 可执行文件 (kubent CLI 工具) |

## 注意事项

- CI 环境必须设置 GOPROXY=https://goproxy.cn,direct 和 GOSUMDB=off
- 编译时间较长 (~9分钟)，因为 Go 需要编译大量 Kubernetes 相关依赖
- 二进制为静态链接，无运行时依赖
- conanfile.py 的 build() 方法使用 shutil.which("go") 查找 go binary，支持 harmonybrew 回退
---

**编译结束**: 2026-07-03 15:53
**最终状态**: built
