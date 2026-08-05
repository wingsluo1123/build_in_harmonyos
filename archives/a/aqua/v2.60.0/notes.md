# aqua 编译笔记

## 基本信息

- 软件名: aqua
- 版本: v2.60.0
- 类型: go 工具
- 上游仓库: https://github.com/aquaproj/aqua
- 编译日期: 2026-08-05

## 编译过程

### 编译方式

Go 项目，使用 `go build` 直接编译：

```bash
# 环境
eval "$(/storage/Users/currentUser/.harmonybrew/bin/brew shellenv)"
export GOPROXY="https://goproxy.cn,direct"
export CGO_ENABLED=0
export GOOS=linux
export GOARCH=arm64

# 编译（使用 ldflags 注入版本号）
cd $BUILD_SRC_DIR
go build -ldflags="-s -w -X main.version=v2.60.0" -o aqua ./cmd/aqua
```

- Go 版本: go1.26.5 (linux/arm64)
- Go 模块: github.com/aquaproj/aqua/v2
- 入口: cmd/aqua/main.go
- 版本注入: `var version = ""` 在 main.go，通过 ldflags `-X main.version=v2.60.0` 设置
- CGO: 禁用 (CGO_ENABLED=0)

### 验证

- 二进制文件: `$TEST_PREFIX/bin/aqua`
- 功能验证: `aqua version` → `v2.60.0` ✅

### 依赖

- 无外部 C/C++ 依赖
- Go 模块依赖通过 GOPROXY 自动解析

## 制品信息

- 制品: `bin/aqua` (23MB, ELF aarch64)

## 备注

此软件为纯 Go 项目，无 C/C++ 依赖，无 configure/make 构建系统。
使用 `go build` 直接编译，通过 ldflags 注入版本号。
---

**编译结束**: 2026-08-05 20:40
**最终状态**: built
