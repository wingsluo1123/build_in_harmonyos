# golangci-lint 2.5.0 适配笔记

## 编译环境
- 构建系统: Go (go build)
- 编译日期: 2026-07-02
- 编译器: clang/clang++ (Go 工具链 go1.24.4 linux/arm64)
- 状态: published

## 编译步骤

1. 下载源码包 v2.5.0.tar.gz（通过 ghfast.top 镜像，因 GitHub SSL 证书验证失败）
2. 解压到 work 目录，执行 `go mod download` 下载 Go 依赖（使用 GOPROXY=https://goproxy.cn,direct）
3. 构建命令：
   ```bash
   cd $BUILD_SRC_DIR
   export CGO_ENABLED=0
   go build -trimpath \
     -ldflags '-s -w -X main.version=2.5.0 -X main.date=2026-07-02 -X main.commit=v2.5.0' \
     -o golangci-lint ./cmd/golangci-lint
   ```
4. 安装到 staging 目录：`cp golangci-lint $TEST_PREFIX$DEFAULT_PREFIX/bin/`
5. 通过 elfldr 测试：`elfldr golangci-lint --version`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载 SSL 证书验证失败 | OHOS 平台缺少 CA 证书链 | 使用 `curl -kL` 手动下载 + ghfast.top 镜像 |
| 2 | 版本显示为 (devel) | ldflags 设置了错误的包路径 | 分析 main.go 源码，改用 `-X main.version=2.5.0 -X main.date=2026-07-02` |
| 3 | conan create 下载源码失败 | conandata.yml 中 GitHub URL SSL 验证失败 | 更新 conandata.yml URL 为 ghfast.top 镜像 |
| 4 | conan create 构建失败 (directory not found) | go build 在 build-release 目录执行而非 source 目录 | 在 build() 中添加 `cd {src}` 切换到 source_folder |

## 源码修改

无源码修改，无补丁。

## 依赖版本

- Go: go1.24.4 (linux/arm64, 通过 elfldr wrapper 运行)
- Conan: 2.30.0 (OHOS 适配版)
- Clang: 15.0.4

## 验证结果

```bash
$ elfldr golangci-lint --version
golangci-lint has version 2.5.0 built with go1.24.4 from v2.5.0 on 2026-07-02

$ elfldr golangci-lint --help
Smart, fast linters runner.

Usage:
  golangci-lint [flags]
```

conan-verify 全部通过（G1-G4, L2/L4/L5）。
conan create test_package 输出：
```
golangci-lint has version 2.5.0 built with go1.24.4 from v2.5.0 on 2026-07-02
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| golangci-lint-2.5.0-linux-arm64.tar.gz | ~34.6 MB | 打包的静态二进制 |
| golangci-lint | 36,241,592 bytes | 静态 ELF 二进制 (arm64) |

## 注意事项

- Go 二进制在 OHOS 上需通过 elfldr wrapper 执行
- conandata.yml 使用 ghfast.top 镜像 URL 解决 GitHub SSL 问题
- Go 版本注入需同时设置 main.version 和 main.date（否则回退到 buildInfo）
---

**编译结束**: 2026-07-02 01:52
**最终状态**: published
