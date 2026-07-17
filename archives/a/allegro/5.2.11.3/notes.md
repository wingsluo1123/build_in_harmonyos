# allegro 5.2.11.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-15
- 状态: built

## 遇到的问题与解决方案
- 无 X11/OpenGL 依赖 (WANT_X11=OFF)
- 示例程序包含 X11 头文件导致编译失败，禁用示例 (WANT_EXAMPLES=OFF)
- CMake function sanitize_cmake_link_flags 使用 ... 变参语法，移除后修复 (patch)
- 构建产物为静态库 (.a)，默认配置 shared=False，包含 allegro 主库和 8 个附加库

## 构建配置
- WANT_X11=OFF: 无 X11 依赖
- ALLEGRO_UNIX=1: Unix 平台构建
- WANT_EXAMPLES=OFF: 禁用示例程序
- WANT_POPUP_EXAMPLES=OFF: 禁用弹窗示例

## 交付物
| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 |
| conandata.yml | 源码 + 补丁声明 |
| test_package/ | 测试包 |
| patches/0001-cmake-Common.cmake.patch | CMake 兼容性补丁 |

## COMPLETED
---

**编译结束**: 2026-07-15 17:31
**最终状态**: built
