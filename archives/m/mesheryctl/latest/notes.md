# mesheryctl latest 适配笔记

## 编译环境
- 构建系统: go (Go module + Makefile wrapper)
- 编译日期: 2026-07-03
- 编译器: go1.26.4 linux/arm64 (clang 15.0.4 for C/C++ if needed)
- 状态: published

## 源码信息
- 仓库: https://github.com/meshery/meshery
- 版本标签: v1.0.52
- 下载URL: https://github.com/meshery/meshery/archive/refs/tags/v1.0.52.tar.gz
- SHA256: 1a1b1ad517e71d1c8faa691f58d165a32b230a9a706b5e681f8d7c13a5ad2684
- 源码大小: ~638MB (完整 monorepo)

## 项目结构说明
mesheryctl 是 Meshery 云原生管理平台的 CLI 工具，位于 meshery/meshery monorepo 的 `mesheryctl/` 子目录中。
- `go.mod` 和 `go.sum` 位于仓库根目录（非 mesheryctl/ 内）
- `mesheryctl/` 包含 CLI 源码（cmd/, internal/, pkg/ 等）
- `server/` 包含 mesheryctl 依赖的服务端模型代码（server/models, server/handlers 等）
- 编译时需要同时提取 mesheryctl/ 和 server/ 目录

## 编译步骤

1. 从 GitHub 下载 v1.0.52 tarball
2. 提取 go.mod, go.sum, mesheryctl/, server/ 到工作目录
3. 设置 GOPROXY=https://goproxy.cn,direct（proxy.golang.org 不可达）
4. 运行 `go mod download` 下载所有 Go 模块依赖
5. 编译命令:
```bash
CGO_ENABLED=0 GOARCH=arm64 GOOS=linux go build \
  -ldflags="-w -s \
    -X github.com/meshery/meshery/mesheryctl/internal/cli/root/constants.version=v1.0.52 \
    -X github.com/meshery/meshery/mesheryctl/internal/cli/root/constants.commitsha=unknown \
    -X github.com/meshery/meshery/mesheryctl/internal/cli/root/constants.releasechannel=edge" \
  -o bin/mesheryctl mesheryctl/cmd/mesheryctl/main.go
```
6. 安装: `cp bin/mesheryctl $DESTDIR$PREFIX/bin/mesheryctl`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 搜索到的 savannah URL 404 | mesheryctl 不是独立 GNU 项目，是 GitHub 上的 Go 项目 | 通过 GitHub API 搜索找到 meshery/meshery 仓库，使用 --url 指定正确的 GitHub tarball URL |
| 2 | Go 模块下载超时 (proxy.golang.org i/o timeout) | OHOS 环境无法访问 Google 服务 (proxy.golang.org) | 设置 GOPROXY=https://goproxy.cn,direct 使用中国镜像 |
| 3 | 编译报 "no required module provides package github.com/meshery/meshery/server/models" | mesheryctl 依赖同 monorepo 的 server/ 子目录，但只提取了 mesheryctl/ | 从 tarball 中额外提取 server/ 目录到工作目录 |
| 4 | 二进制创建在 mesheryctl/ 目录内而非顶层 | -o mesheryctl 与 mesheryctl/ 目录名冲突 | 修改 Makefile，输出到 bin/mesheryctl |

## 源码修改

创建了顶层 Makefile（原始仓库中 mesheryctl/Makefile 引用了 ../install/ 中的文件，无法直接使用）:
- `Makefile`: 封装 go build 命令，提供 build/install/check/clean 目标

## 依赖版本

- Go: 1.26.4 (linux/arm64)
- 主要 Go 依赖:
  - github.com/meshery/meshkit v1.0.19
  - github.com/meshery/schemas v1.3.22
  - k8s.io/client-go v0.35.2
  - github.com/docker/docker v28.5.2+incompatible
  - github.com/spf13/viper v1.21.0
  - google.golang.org/api v0.287.0

## 验证结果

```bash
$ file bin/mesheryctl
ELF executable, 64-bit LSB arm64, static, BuildID=..., stripped

$ bin/mesheryctl --help
As a self-service engineering platform, Meshery enables collaborative design
and operation of cloud native infrastructure.
...
Usage:
  mesheryctl [flags]
  mesheryctl [command]
...
```

## 产物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/mesheryctl | ~108MB | 静态链接 ELF 二进制，arm64，stripped |

## 注意事项

1. 编译前必须设置 GOPROXY=https://goproxy.cn,direct，否则 Go 模块下载会超时
2. 需要同时提取 mesheryctl/ 和 server/ 目录（mesheryctl 依赖 server/models 等包）
3. go.mod/go.sum 位于仓库根目录，不是 mesheryctl/ 内
4. 二进制是纯静态链接（CGO_ENABLED=0），无外部 .so 依赖
5. Conan 配方中的 build() 方法需要能找到 go binary（shutil.which("go") → harmonybrew → 报错）
---

**编译结束**: 2026-07-03 15:05
**最终状态**: built
