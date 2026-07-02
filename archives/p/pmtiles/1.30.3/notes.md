# pmtiles 1.30.3 适配笔记

## 编译环境
- 构建系统: Go (go build)
- 编译日期: 2026-07-02
- 编译器: ohos_golang_go go1.24.5 + clang/clang++ (OHOS SDK 26.0.0.18)
- 状态: built

## 编译步骤

### 1. 源码下载
```bash
# GitHub 直连超时，使用 ghproxy.net 代理下载
curl -L https://ghproxy.net/https://github.com/protomaps/go-pmtiles/archive/refs/tags/v1.30.3.tar.gz -o pmtiles-1.30.3.tar.gz
tar xf pmtiles-1.30.3.tar.gz
mv go-pmtiles-1.30.3 pmtiles-1.30.3
```

### 2. go.mod 降级 (参考 Go 适配指南 §3.3)
```bash
# 编辑 go.mod: go 1.25.0 → go 1.24
# 删除 toolchain 行
# 降级 golang.org/x/* 包到 go 1.24 兼容版本
go get golang.org/x/crypto@v0.48.0
go get golang.org/x/net@v0.50.0
go get golang.org/x/sys@v0.41.0
go get golang.org/x/term@v0.40.0
go get golang.org/x/text@v0.34.0
go get golang.org/x/time@v0.14.0
go get golang.org/x/oauth2@v0.35.0
go mod tidy -e
```

### 3. 交叉编译
```bash
export GOROOT=/storage/Users/currentUser/ohos-go
export PATH=$GOROOT/bin:$PATH
export GOTOOLCHAIN=local
export GOOS=openharmony
export GOARCH=arm64
export CGO_ENABLED=1
export AR=.../llvm-ar
export CC=.../aarch64-unknown-linux-ohos-clang
export CXX=.../aarch64-unknown-linux-ohos-clang++
export GOPROXY=https://goproxy.cn,direct
export GOFLAGS=-mod=mod

go build -o pmtiles -ldflags "-X main.version=1.30.3 -X main.commit=v1.30.3 -X main.date=2026-07-02" .
```

### 4. 签名验证
```bash
binary-sign-tool sign -selfSign 1 -inFile pmtiles -outFile pmtiles.signed -signAlg SHA256withECDSA
./pmtiles version  # pmtiles 1.30.3, commit v1.30.3, built at 2026-07-02
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 直连超时 | 网络限制 | 使用 ghproxy.net 代理下载源码 |
| 2 | go mod tidy 失败: proxy.golang.org EOF | 网络限制 | 设置 GOPROXY=https://goproxy.cn,direct |
| 3 | caddy v2.11.2 要求 go >= 1.25.0 | 依赖版本过高 | 移除 caddy/ 目录 (CLI 工具 main.go 不依赖 caddy) |
| 4 | golang.org/x/crypto v0.49.0 要求 go >= 1.25.0 | x/ 包版本过高 | 降级到 v0.48.0 (go 1.24.0) |
| 5 | golang.org/x/net v0.52.0 要求 go >= 1.25.0 | x/ 包版本过高 | 降级到 v0.50.0 (go 1.24.0) |
| 6 | golang.org/x/sys v0.42.0 要求 go >= 1.25.0 | x/ 包版本过高 | 降级到 v0.41.0 (go 1.24.0) |
| 7 | golang.org/x/term v0.41.0 要求 go >= 1.25.0 | x/ 包版本过高 | 降级到 v0.40.0 (go 1.24.0) |
| 8 | golang.org/x/text v0.35.0 要求 go >= 1.25.0 | x/ 包版本过高 | 降级到 v0.34.0 (go 1.24.0) |
| 9 | golang.org/x/time v0.15.0 要求 go >= 1.25.0 | x/ 包版本过高 | 降级到 v0.14.0 (go 1.24.0) |
| 10 | golang.org/x/oauth2 v0.36.0 要求 go >= 1.25.0 | x/ 包版本过高 | 降级到 v0.35.0 (go 1.24.0) |
| 11 | go build 输出到 pmtiles 目录名冲突 | pmtiles 既是目录名也是输出名 | 二进制生成在 pmtiles/go-pmtiles，手动复制重命名 |
| 12 | Conan 配方生成使用 Autotools 模板 | SKILL 框架不支持 Go 项目 | conanfile.py 不适用于 Go，conan-verify G1 失败 |

## 源码修改

### go.mod 修改
- `go 1.25.0` → `go 1.24`
- 删除 `toolchain` 行
- 降级 7 个 golang.org/x/* 间接依赖到 go 1.24 兼容版本
- 移除 caddy/ 目录 (Caddy 插件包，CLI 工具不需要)

### 未修改的源文件
- main.go: 未修改
- pmtiles/*.go: 未修改
- 所有业务逻辑代码未修改

## 依赖版本

| 依赖 | 原版本 | 降级后版本 | go 要求 |
|------|--------|-----------|---------|
| golang.org/x/crypto | v0.49.0 | v0.48.0 | 1.24.0 |
| golang.org/x/net | v0.52.0 | v0.50.0 | 1.24.0 |
| golang.org/x/sys | v0.42.0 | v0.41.0 | 1.24.0 |
| golang.org/x/term | v0.41.0 | v0.40.0 | 1.24.0 |
| golang.org/x/text | v0.35.0 | v0.34.0 | 1.24.0 |
| golang.org/x/time | v0.15.0 | v0.14.0 | 1.24.0 |
| golang.org/x/oauth2 | v0.36.0 | v0.35.0 | 1.24.0 |
| github.com/caddyserver/caddy/v2 | v2.11.2 | 移除 | N/A (CLI 不需要) |

## 验证结果

```bash
$ file /storage/Users/currentUser/pmtiles
/storage/Users/currentUser/pmtiles: ELF executable, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), BuildID=e39fadc4e74e86dd764b8bd52683c60c1adc31df, not stripped

$ /storage/Users/currentUser/pmtiles version
pmtiles 1.30.3, commit v1.30.3, built at 2026-07-02

$ /storage/Users/currentUser/pmtiles --help
Usage: pmtiles <command>
  show / tile / cluster / edit / extract / makesync / merge / region / serve / show / sync / tilejson / upload / verify / version
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| /storage/Users/currentUser/pmtiles | 126MB | 签名后的 OpenHarmony aarch64 二进制 |

## Conan 配方状态

- **状态**: 未通过 (conan-verify G1 失败)
- **原因**: SKILL 框架的 conan-init 命令仅支持 C/C++ 构建系统 (autotools/cmake/makefile)，不识别 Go 项目的 go.mod 构建系统。生成的 conanfile.py 使用了 Autotools 模板，无法正确编译 Go 项目。
- **建议**: 如需 Conan 打包，需手动编写 Go 专用的 conanfile.py，在 build() 方法中调用 `go build` 命令。

## 注意事项

1. 二进制大小 126MB，因 Go 静态编译包含运行时和所有依赖 (AWS/Azure/GCP SDK 等)
2. pmtiles 使用 zombiezen.com/go/sqlite (纯 Go SQLite 实现)，CGO_ENABLED=1 可用但非必需
3. 版本信息通过 ldflags 注入: `-X main.version=1.30.3`
4. caddy/ 目录是 Caddy HTTP 服务器插件，CLI 工具 (main.go) 不依赖它，可安全移除
5. GOPROXY 必须设置为 https://goproxy.cn,direct (proxy.golang.org 不可达)
6. GOTOOLCHAIN=local 必须设置，防止 Go 自动下载高版本工具链
---

**编译结束**: 2026-07-02 14:24
**最终状态**: built
