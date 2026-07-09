# lazygit

**一个简洁的 Git 终端 UI 工具**

- **主页**: https://github.com/jesseduffield/lazygit
- **许可证**: MIT
- **编程语言**: Go

## 简介

lazygit 是一个 Git 命令的终端 UI 工具，提供交互式界面来执行暂存、提交、推送等常见 Git 操作，无需记忆复杂的 Git 命令语法。

## 版本

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| 0.48.0 | published | 2026-07-02 |

## 编译说明 (0.48.0)

- **构建系统**: Go (go build，使用 vendor 目录)
- **Go 版本**: go1.24.4 linux/arm64
- **CGO**: 已启用 (tcell 终端 UI 库依赖 cgo)
- **依赖模式**: -mod=vendor (使用源码自带的 vendor 目录)
- **二进制类型**: ELF64 AArch64，静态链接 (无动态段)
- **二进制大小**: ~19MB
- **运行方式**: 在 OHOS 上通过 elfldr 加载器运行

## OHOS 适配说明

lazygit 是纯 Go 项目，在 OHOS 平台上使用标准 Go 工具链即可编译通过，无需修改源码。二进制为静态链接，通过 elfldr ELF 加载器在 OHOS 平台上运行。

### 编译命令
```bash
CGO_ENABLED=1 GOFLAGS=-mod=vendor \
  go build -trimpath \
  -ldflags '-s -w -X main.commit=v0.48.0 -X main.version=0.48.0 -X main.date=2025-01-01' \
  -o lazygit .
```

### 版本验证
```bash
$ elfldr lazygit --version
commit=v0.48.0, build date=2025-01-01, build source=unknown, version=0.48.0, os=linux, arch=arm64, git version=2.45.2
```
