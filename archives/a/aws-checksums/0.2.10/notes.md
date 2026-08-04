# aws-checksums 0.2.10 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-05
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤
标准 CMake 构建，静态库模式。

## 依赖关系
- aws-c-common/0.12.6 (Conan 制品仓未发布，CI 从源码构建)

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | AWS CMake 模块未找到 | aws-c-common conan recipe 未暴露 CMAKE_MODULE_PATH | 在 generate() 中通过 helper cmake 文件 list(APPEND CMAKE_MODULE_PATH ...) |
| 2 | AWS:: target 命名空间不匹配 | conan CMakeDeps 生成 aws-c-common:: 而非 AWS:: | 添加 0001-cmake-alias-target.patch 创建别名 |
| 3 | test_package 找不到 aws-c-common 头文件 | aws-c-common recipe 未设置 cpp_info.includedirs | test_package CMakeLists.txt 手动添加 include path |

## 上游测试
- 17/17 测试通过
- CRC32, CRC32C, CRC64, xxHash 全部正常

## 结束
status: closed
COMPLETED
