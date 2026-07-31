# meek 0.38.0 适配笔记

## 编译环境
- 构建系统: go
- 编译日期: 2026-07-31
- 编译器: go
- 状态: built

## 编译步骤

1. 下载源码包并解压
2. 设置 Go 交叉编译环境变量：
   - `CGO_ENABLED=0`（纯 Go 静态链接，R26）
   - `GOOS=linux`（HarmonyOS 使用 Linux 内核，Go 不支持 ohos）
   - `GOARCH=arm64`（arm64 目标架构，映射 Conan arch=armv8）
3. 构建 meek-client：`go build -trimpath -ldflags "-s -w" -o meek-client ./meek-client`
4. 构建 meek-server：`go build -trimpath -ldflags "-s -w" -o meek-server ./meek-server`
5. 复制二进制到 bin/ 目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go 不识别 OHOS 平台 | Go 的 GOOS 不支持 "ohos" | 映射为 GOOS=linux（HarmonyOS 内核为 Linux） |
| 2 | Conan arch 与 Go arch 命名不一致 | Conan 用 armv8，Go 用 arm64 | 在配方中映射 armv8/aarch64 → arm64 |
| 3 | Go 依赖管理 | meek 使用 go.mod 管理 Go 模块依赖 | 使用 GOFLAGS=-mod=mod 允许自动下载 |

## 源码修改

无补丁。meek 源码无需修改即可在 HarmonyOS 上编译。

## 依赖版本

- Go 工具链（CI 环境提供，>= 1.21）
- Go modules（go.mod 管理，构建时自动下载）

## 验证结果

```bash
# meek-client 无环境变量运行，预期输出 ENV-ERROR 并退出码 1
meek-client 2>/dev/null
# 输出: ENV-ERROR no TOR_PT_MANAGED_TRANSPORT_VER

# meek-server 无环境变量运行，预期输出 ENV-ERROR 并退出码 1
meek-server 2>/dev/null
# 输出: ENV-ERROR no TOR_PT_MANAGED_TRANSPORT_VER
```

## 注意事项

- meek 是 Go 项目，依赖通过 go.mod 管理，非 Conan 依赖
- CGO_ENABLED=0 确保纯静态链接，无 C 库依赖
- 交叉编译时需正确设置 GOOS/GOARCH（R33）
- test_package 包含 cross_building 检查，x86_64 CI 跳过二进制执行
