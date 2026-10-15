# plank 0.11.89 — 适配笔记

## 基本信息
- 上游: https://github.com/osen/plank (master branch, no tags/releases)
- 构建系统: CMake (cmake_minimum_required 2.6)
- 产物: libplank.a (C) + libplankmm.a (C++ wrapper)
- 依赖: 无第三方依赖，仅 POSIX libc

## 源码 musl 兼容性扫描

### POSIX API 使用
| API | 文件 | musl 兼容 | 说明 |
|-----|------|-----------|------|
| mmap() | palloc.c, plank.cpp | ✅ | MAP_PRIVATE \| MAP_ANONYMOUS 分配内存页 |
| mprotect() | palloc.c, plank.cpp | ✅ | PROT_NONE 标记 freed 内存为禁止访问 |
| munmap() | plank.cpp | ✅ | 释放 zombie 内存页 |
| atexit() | palloc.c, plank.cpp | ✅ | 注册退出时统计输出 |
| calloc/free | palloc.c, plank.cpp | ✅ | 元数据分配 |
| getpagesize() | palloc.c, plank.cpp | ✅ | 获取内存页大小 (musl 支持) |

### Windows-only 代码
所有 Windows API (VirtualAlloc/VirtualProtect) 均在 `#ifdef _WIN32` 守卫内，
OHOS 走 POSIX 代码路径，无影响。

### 补丁清单
1. `0001-src-plankmm-plank.cpp.patch` (portability)
   - 问题: C++17 移除了动态异常规范 (throw(std::bad_alloc), throw())
   - 修复: throw(std::bad_alloc) → noexcept(false), throw() → noexcept
   - 行号: 214, 223, 228, 237

## CMake 参数
- CMAKE_POLICY_VERSION_MINIMUM=3.5 (兼容 CMake 4.x)
- CMAKE_SYSTEM_NAME=Linux (E092: CMake 无 HarmonyOS 平台模块)
- BUILD_SHARED_LIBS=OFF (静态库, Conan Toolchain 默认)

## 上游测试
- 8 个测试: ctest1-4 (C) + cxxtest1-4 (C++)
- 测试框架: 无框架, 自定义可执行文件
- CMakeLists.txt 定义 add_executable + target_link_libraries

## test_package
- test_plank.c: palloc/pfree API 验证 (5 assertions, 100 alloc/free 循环)
