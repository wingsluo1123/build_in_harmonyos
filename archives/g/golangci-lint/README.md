# golangci-lint

Go linters runner — aggregates 100+ Go linters with smart configuration.

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 2.5.0 | published | Go 项目，go build 编译，OHOS aarch64 适配 |

## 描述

golangci-lint is a fast Go linters runner. It runs linters in parallel, caches
their results, and uses a smart approach to minimize CPU usage. It integrates
100+ Go linters and provides a unified configuration interface.

## 构建信息

- **语言**: Go
- **构建系统**: `go build`
- **Go 版本**: go1.24.4
- **License**: MIT
- **主页**: https://github.com/golangci/golangci-lint

## OHOS 适配要点

- CGO_ENABLED=0 纯静态编译
- 通过 elfldr wrapper 执行
- conandata.yml 使用 ghfast.top 镜像 URL
