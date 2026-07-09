# k9s

Kubernetes 终端管理工具（TUI）—— 在终端中浏览和管理 Kubernetes 集群。

k9s 提供基于 tcell 的终端界面，用于与 Kubernetes 集群交互，包括浏览资源、查看日志、进入 Pod 执行命令、以及执行常见的集群管理操作。

## 版本列表

| 版本 | 状态 | 构建系统 | 编译日期 |
|------|------|---------|---------|
| 0.50.16 | ✅ 已发布 (published) | Go (go build) | 2026-07-02 |

## 主页
https://github.com/derailed/k9s

## 许可证
Apache-2.0

## 构建说明
- Go 项目，使用 `go build` 构建，CGO_ENABLED=0（纯 Go 静态二进制）
- 需要 Go >= 1.24.4（依赖链要求此版本）
- OHOS 平台上 Go 工具二进制需要 elfldr wrapper 才能运行
- tcell 终端 UI 使用 syscall，无需 C 依赖
- 功能测试覆盖：version、info、--help、completion bash、kubeconfig 读取等 10 项
