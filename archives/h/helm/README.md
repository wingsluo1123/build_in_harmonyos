# Helm

Helm is the package manager for Kubernetes. It helps you manage Kubernetes applications — Helm Charts help you define, install, and upgrade even the most complex Kubernetes application.

## 版本

- **3.19.0** (2026-07-01, built on OHOS)

## 描述

Helm is a tool for managing Kubernetes charts. Charts are packages of pre-configured Kubernetes resources.

Use Helm to:
- Find and use popular software packaged as Kubernetes Charts
- Share your own applications as Kubernetes Charts
- Create reproducible builds of your Kubernetes applications
- Intelligently manage your Kubernetes manifest files
- Manage releases of Helm packages

## 构建信息

- **语言**: Go
- **构建系统**: `go build` (非 autotools/cmake)
- **源码**: https://github.com/helm/helm/archive/refs/tags/v3.19.0.tar.gz
- **许可证**: Apache-2.0
- **主页**: https://helm.sh

## OHOS 适配说明

helm 是纯 Go 项目，使用 `go build` 编译为静态二进制，天然跨平台兼容。
在 OHOS 上需要通过 ELF 加载器 (elfldr) 运行，因为 OHOS 内核不支持直接执行静态 ELF 二进制。

### 关键编译参数
```bash
CGO_ENABLED=0 go build -trimpath -ldflags '-w -s' -o bin/helm ./cmd/helm
```

### Go 版本要求
helm 3.19.0 的 go.mod 要求 go >= 1.24.0。需安装 Go 1.24.0 并为工具链子工具创建 ELF wrapper 脚本。
