# aztfexport 0.19.0 适配笔记

## 编译环境
- 构建系统: Go (custom)
- 编译日期: 2026-07-03
- Go 版本: 1.26.4
- 平台: OpenHarmony aarch64
- 状态: published

## 编译步骤

aztfexport 是纯 Go 项目，使用 Go toolchain 直接编译：

```bash
cd $BUILD_SRC_DIR
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 \
  GOPROXY=https://goproxy.cn,direct \
  go build -trimpath \
  -ldflags="-s -w -X 'main.version=0.19.0' -X 'main.revision=conan'" \
  -o aztfexport .
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | search-url 返回错误的 GNU 镜像站 URL | aztfexport 不在 GNU Savannah，脚本误匹配 | 手动指定 GitHub release URL |
| 2 | test_package 模板使用 CMake find_package | 纯 Go 二进制没有 CMake targets | 改为直接运行 `aztfexport version` 验证 |

## 源码修改

无补丁，纯 Go 项目原生支持 linux/arm64 目标。

## 依赖版本

无 C/C++ 依赖。Go 工具链由系统提供（Go 1.26.4）。

## 验证结果

```bash
aztfexport version  # 输出版本信息确认二进制可用
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（Go build） |
| conandata.yml | 源码 URL + SHA256 |
| test_package/ | 消费者验证（go version check） |
