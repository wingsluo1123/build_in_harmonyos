# sloci-image

## 简介

sloci-image 是一个简单的 POSIX shell 脚本工具，用于创建单层 OCI 容器镜像。
它符合 OCI Image Format 1.0.1 规范，只需 POSIX sh 和常见 Unix 工具即可运行。

## 功能概述

- **单层 OCI 镜像创建**：将 rootfs 目录或 tar.gz 压缩包打包为单层 OCI 镜像
- **轻量级**：纯 shell 脚本实现，无需 Go 或其他运行时
- **OCI 规范兼容**：符合 OCI Image Format 1.0.1

## OHOS 适配要点

### 1. 无需编译

sloci-image 是纯 shell 脚本，在 HarmonyOS 环境下直接可用。
构建过程仅执行 `make install` 将脚本安装到指定目录。

### 2. 运行依赖

- POSIX sh 兼容 shell（如 dash, bash）
- 常见 Unix 工具：awk, date, gzip, sed, sha256sum, tar

## 依赖关系

### 编译依赖
无（纯 shell 脚本工具）

### 运行依赖
- POSIX sh
- awk, date, gzip, sed, sha256sum, tar

## 参考资料

- 官网：https://github.com/jirutka/sloci-image
- 许可证：MIT
