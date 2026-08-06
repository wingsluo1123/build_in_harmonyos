# github-mcp-server 1.2.0 编译笔记

## 基本信息
- 软件: github-mcp-server
- 版本: 1.2.0
- 构建系统: Go (go build)
- 构建模式: conan (Conan 2.x recipe)
- 架构: aarch64 (arm64)
- 日期: 2026-08-06

## 编译过程
- 源码获取: GitHub archive tarball (https://github.com/github/github-mcp-server/archive/refs/tags/v1.2.0.tar.gz)
- SHA256: 02b3865518fa189d066a14d81b891e939e93b60bb1723eeea728f4720d1a1e60
- 编译命令: `CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -ldflags "-X main.version=1.2.0 -X main.commit=v1.2.0" -o github-mcp-server ./cmd/github-mcp-server/`
- 附加二进制: mcpcurl (`CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -o mcpcurl ./cmd/mcpcurl/`)
- 安装方式: Conan package (bin/ directory)
- Strip: 不 strip（HarmonyOS MAC 安全策略禁止执行 stripped ELF 二进制）

## 关键决策
- GitHub archive URL 作为 conandata.yml 源码地址 (R39: 官方源)
- CI 自动添加 GitHub 镜像 fallback (gh-proxy.com 等)
- GOPROXY 设为 goproxy.cn,direct 以解决 Go module 下载问题
- CGO_ENABLED=0 静态编译，无外部 C 库依赖
- 编译两个二进制: github-mcp-server (主程序) + mcpcurl (辅助工具)
- Go toolchain 通过 Harmonybrew 安装 (brew install go)
- package_type = "application" (命令行工具，非库)
- commands.json 声明在软件级别目录 (R38)

## 遇到的问题及解决
1. **Go 未安装**: 系统未预装 Go → 通过 Harmonybrew 安装 (brew install go)
2. **GitHub 无法直接访问**: github.com 443端口无法连接 → CI 自动添加镜像 fallback; 本地通过 goproxy.cn 获取 Go module 源码
3. **Go module cache 只读**: go.sum 条目缺失 → 复制源码到可写目录后 go mod download
4. **HarmonyOS tmpfs 禁止执行**: 从 golang.google.cn 下载的 Go binary 无法执行 (MAC 策略) → 使用 Harmonybrew 安装的 Go (可执行)

## 质量门禁结果
- G1: ✅ 配方完整性通过
- G2: ✅ conan create 验证通过
- R34: ✅ test_package 实质测试 (--version 执行)
- R38: ✅ commands.json 声明

## 产出文件
- github-mcp-server: 25MB ELF arm64 static binary
- mcpcurl: 6.8MB ELF arm64 static binary
---

**编译结束**: 2026-08-06
**最终状态**: built (Conan adapted)
