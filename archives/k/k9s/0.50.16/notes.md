# k9s 0.50.16 适配笔记

## 编译环境
- 构建系统: Go (go build)
- 编译日期: 2026-07-02
- 编译器: Go 1.24.4 (linux/arm64)
- 状态: published

## 编译步骤

1. 下载 Go 1.24.4（go.mod 要求 go >= 1.24.4，系统原有 Go 1.24.0）
2. 为 Go 1.24.4 工具链创建 elfldr wrapper（pkg/tool/linux_arm64/ 目录下的 compile/link/asm 等工具需要 elfldr 运行）
3. 修改 go wrapper 脚本指向 1.24.4 并设置 GOTOOLCHAIN=auto
4. 使用 `go build` 编译 k9s

```bash
export CGO_ENABLED=0
go build -trimpath -ldflags '-s -w -X github.com/derailed/k9s/cmd.version=v0.50.16' -tags netgo -o k9s .
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | OHOS 缺少系统 CA 证书 | 设置 SSL_CERT_FILE 指向已安装的 cert.pem |
| 2 | go.mod 要求 go >= 1.24.4，系统只有 1.24.0 | k9s 0.50.16 依赖链要求较新 Go | 下载安装 Go 1.24.4，创建 elfldr wrapper |
| 3 | GOTOOLCHAIN=local 硬编码 | Go 1.24.0 编译时设为 local 默认值 | 修改 go wrapper 脚本设置 GOTOOLCHAIN=auto |
| 4 | Go 工具链 permission denied | Go 1.24.4 工具二进制需要 elfldr | 将真实二进制移至 .real/，创建 wrapper 脚本 |

## 源码修改

无源码修改。仅修改了 go wrapper 脚本以使用 Go 1.24.4。

## 依赖版本

- Go: 1.24.4
- CGO_ENABLED=0（纯 Go 静态二进制，tcell 使用 syscall 无需 C 依赖）

## 验证结果

```bash
$ elfldr k9s version
Version:    v0.50.16
Commit:     dev
Date:       n/a
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| k9s | ~125MB | 静态 ELF 二进制 (arm64) |

## 注意事项

- k9s 是 Go 项目，conanfile.py 使用 `go build` 而非 autotools/cmake
- 需要安装 Go 1.24.4+（go.mod 依赖链要求）
- Go 工具链需要 elfldr wrapper 才能在 OHOS 上运行
- CGO_ENABLED=0 即可编译，tcell 终端 UI 不需要 cgo
---

**编译结束**: 2026-07-02 01:36
**最终状态**: published
