# actionlint

## 软件描述

actionlint 是一个 GitHub Actions 工作流文件的静态检查器（linter）。它能够检测工作流 YAML 文件中的语法错误、已废弃的语法、不安全的用法以及其他常见问题，帮助开发者在提交前发现潜在的错误。

## 功能概述

- 检查 GitHub Actions 工作流 YAML 文件的语法和语义错误
- 验证 `uses` 引用的 Action 格式（owner/repo@ref）
- 检查矩阵策略（matrix strategy）配置
- 验证 `runs-on` 标签
- 检查 `needs` 依赖关系
- 验证环境变量引用
- 支持 shell 命令检查（集成 shellcheck）
- 支持 JSON 格式输出（便于 CI 集成）
- 内置所有 GitHub Webhook 事件和 Popular Actions 元数据

## OHOS 适配

- **构建系统**: Go 语言项目，使用 `go build` 编译，无需 autotools/cmake
- **编译方式**: `CGO_ENABLED=0 go build -trimpath`，生成纯静态二进制
- **运行方式**: OHOS 平台上需通过 `elfldr` 加载运行
- **版本注入**: 通过 `-ldflags '-X github.com/rhysd/actionlint.version=1.7.9'` 注入版本号
- **Go 工具链**: OHOS 上的 Go 1.24.0 已由 elfldr 包装，`go build` 可直接使用
- **无外部依赖**: 编译和运行均无外部 C 库依赖

## 依赖关系

- **编译依赖**: Go 1.24.0+ 工具链
- **运行依赖**: 无（纯静态二进制，需 elfldr 加载）
- **可选依赖**: shellcheck（用于 shell 命令检查功能，非必需）

## 参考资料

- 官方网站: https://github.com/rhysd/actionlint
- 源码仓库: https://github.com/rhysd/actionlint
- 文档: https://github.com/rhysd/actionlint/tree/main/docs
