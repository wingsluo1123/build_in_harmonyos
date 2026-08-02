# git-who

## 软件说明

git-who 是一个 Git blame 查看器，为文件树提供高级 blame 操作。用 Go 编写，编译为单二进制文件。

## 功能概述

- **文件树 blame**：递归显示整个文件树的 blame 信息
- **作者统计**：按作者聚合 blame 行数
- **快速渲染**：Go 实现，大仓库也能快速 blame

## OHOS 适配

### 关键问题

1. **E154 - go 工具链缺失**：
   - CI worker 不预装 go
   - 解决方案：通过 cmd-pkgs 预编译包安装 go 1.21.13
   - fallback：试系统 go

2. **交叉编译**：
   - GOOS=linux GOARCH=arm64 CGO_ENABLED=0
   - GOPROXY=https://goproxy.cn,direct（国内镜像加速）

### 与 Linux 的差异

- **无 C 编译器**：CGO_ENABLED=0，纯 Go 编译
- **无 build_type**：Go 无 debug/release 概念，ldflags -s -w strip 符号

## 依赖关系

### 编译依赖
- **go/1.21.13**：通过 cmd-pkgs 安装（制品仓无 conanfile 不能 requires）

### 运行依赖
- **git**：必须，git-who 是 git 的扩展

## 参考资料

- 官方仓库：https://github.com/sinclairtarget/git-who
