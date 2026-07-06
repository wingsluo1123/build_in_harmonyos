# vacuum 0.29.9 适配笔记

## 构建信息
- 构建系统: Go (go 1.26.4)
- 源码: GitHub releases tarball
- 构建命令: go build -ldflags "-X main.version=v0.29.9 -X main.commit=..."
- 目标平台: OHOS aarch64
- CGO: 禁用 (纯 Go 项目)

## 适配要点
1. 纯 Go 项目, 无需 C 依赖
2. 原生 `go build` 直接编译成功
3. 静态链接 ELF arm64 二进制
4. html-report UI 需要 Node.js + npm 构建 UI 资源, 当前为无 UI 基础版

## 可用命令
- vacuum lint — lint OpenAPI/AsyncAPI/JSON Schema
- vacuum dashboard — 交互式仪表盘
- vacuum docs — 生成文档
- vacuum bundle — 打包规范
- vacuum version — 显示版本

## 注意事项
- html-report 命令需要 `html_report_ui` build tag 和 UI 资源预构建
- 二进制约 81MB (静态链接)
