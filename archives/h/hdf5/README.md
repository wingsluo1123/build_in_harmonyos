# HDF5

## 简介

HDF5 (Hierarchical Data Format version 5) 是一款高性能数据管理和存储库，专为大规模科学数据设计。支持多种数据类型，提供高效的 I/O 操作，广泛应用于气象、天文学、基因组学等领域。

## OHOS 适配

- **构建系统选择**：推荐使用 CMake 构建，autotools 在鸿蒙环境可能遇到 config.status 权限问题
- **平台识别**：GNU config.guess/config.sub 需添加 HarmonyOS/ohos 支持（仅用于 autotools）
- **CMake 警告**：CMake 会输出 "System is unknown to cmake" 警告，但不影响编译
- **库类型**：同时生成静态库(.a)和动态库(.so)，默认链接动态库

## 依赖

- zlib: 系统预装版本

## 功能验证

```bash
h5dump --version
h5ls --version
h5diff --version
```

## 可用工具

编译后提供以下工具：
- `h5dump` - HDF5 文件内容导出
- `h5ls` - HDF5 文件内容列表
- `h5diff` - HDF5 文件差异比较
- `h5copy` - HDF5 文件复制
- `h5repack` - HDF5 文件重打包

## 参考

- 官网: https://www.hdfgroup.org/solutions/hdf5/
- 文档: https://docs.hdfgroup.org/hdf5/
- 源码: https://support.hdfgroup.org/ftp/HDF5/releases/