# orocos-kdl 1.5.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-16
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

```bash
# 1. 安装依赖 Eigen3
# Eigen3 为 header-only 库，从 GitLab 下载安装到 ~/usr/local/include/eigen3
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- eigen 3.4.0

# 2. CMake 配置
cmake -B build -S . \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=clang \
  -DCMAKE_CXX_COMPILER=clang++ \
  -DEIGEN3_INCLUDE_DIR=$DEFAULT_PREFIX/include/eigen3

# 3. 编译
cmake --build build -j2

# 4. 安装
cmake --install build --prefix $TEST_PREFIX/$DEFAULT_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | monorepo 结构，源码在 orocos_kdl 子目录 | GitHub 仓库包含多个子项目（orocos_kdl、kdl_parser 等） | init-build 自动检测嵌套源码并提升到顶层；conan recipe 中 configure 使用 build_script_folder="orocos_kdl" |
| 2 | 依赖 Eigen3 未安装 | header-only 线性代数库，非系统默认包含 | 从 cmd-pkgs 安装 eigen/3.4.0 预编译包 |
| 3 | /tmp 只读文件系统 | 鸿蒙平台限制 | 使用 $TMPDIR 环境变量路径 |

## 源码修改

无补丁，源码无需修改即可编译。

## 依赖版本

- Eigen3: 3.4.0 (header-only, 通过 cmd-pkgs 安装)

## 验证结果

```bash
# 编译验证
$ cmake --build build -j2
[100%] Built target orocos-kdl

# 安装验证
$ cmake --install build --prefix $TEST_PREFIX/$DEFAULT_PREFIX
-- Install configuration: "Release"
-- Installing: .../lib/liborocos-kdl.so
-- Installing: .../include/kdl/*.hpp
-- Installing: .../share/orocos_kdl/cmake/*.cmake

# 产物清单
- liborocos-kdl.so (共享库)
- include/kdl/*.hpp (C++ 头文件)
- lib/pkgconfig/orocos-kdl.pc (pkg-config)
- share/orocos_kdl/cmake/ (CMake 配置)
```

## 注意事项

- orocos-kdl 是 C++ 库，需要 C++17 编译
- Eigen3 为 header-only 依赖，无需编译
- 上游测试需要 cppunit 依赖，本次未启用 (ENABLE_TESTS=OFF)
- 属于库类型产物，无需 commands.json
---

**编译结束**: 2026-07-16 15:04
**最终状态**: built
