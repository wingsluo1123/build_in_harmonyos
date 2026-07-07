# git-who 1.3 适配笔记

## 构建信息
- 构建系统: Go (go 1.26.4)
- 源码: GitHub releases tarball
- 构建命令: `go build -ldflags "-s -w -X main.version=v1.3" -o git-who .`
- 目标平台: OHOS aarch64
- CGO: 禁用 (纯 Go 项目)

## 适配要点
1. 纯 Go 项目, 无需 C 依赖
2. 原生 `go build` 直接编译成功
3. 静态链接 ELF arm64 二进制 (3.5MB)
4. Go 模块依赖: golang.org/x/term, golang.org/x/sys, doublestar, go-runewidth

## 可用命令
- `git-who table` — 按作者显示贡献表
- `git-who tree` — 按文件树显示贡献
- `git-who hist` — 按时间线显示贡献
- `git-who -version` — 显示版本

## 注意事项
- 二进制需在 git 仓库目录中运行
- 首次运行可能较慢（分析 git 历史）
