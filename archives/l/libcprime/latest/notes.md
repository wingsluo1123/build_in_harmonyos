# libcprime latest 适配笔记

## 编译环境
- 构建系统: cmake (原项目使用 qmake，创建 CMakeLists.txt)
- 编译日期: 2026-08-06
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: https://api.github.com/repos/rahmanshaber/libcprime/tarball/master
2. 创建 CMakeLists.txt（原项目只有 .pro 文件，qmake 在 OpenHarmony 不可用）
3. 修复 Qt6 API 兼容性问题
4. cmake configure + make

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | qmake 无法生成 Makefile | OpenHarmony 不支持 qmake | 创建 CMakeLists.txt |
| 2 | QList::toSet().toList() 编译失败 | Qt6 移除了 toSet() | 用 QSet 构造函数替代 |
| 3 | QFontMetrics::width() 编译失败 | Qt6 移除了 width() | 用 horizontalAdvance() 替代 |
| 4 | QString::sprintf() 编译失败 | Qt6 移除了 sprintf() | 用 split() 替代 |
| 5 | QDir 构造函数参数不匹配 | Qt6 改变了 QDir 构造函数 | 用 setFilter() 替代 |

## 源码修改

- 0001-add-cmake-build.patch: 新增 CMakeLists.txt
- 0002-qt6-compat.patch: Qt6 API 兼容性修复 (4个文件)

## 依赖版本

- qtbase/6.11.1 (from ohpcd remote)

## 验证结果

```bash
conan create archives/l/libcprime/latest -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# 100% tests passed, 0 tests failed out of 1
```

## 注意事项

- qtbase 使用 cmake_find_mode=none，conan 配方需要设置 CMAKE_PREFIX_PATH
- CMakeDeps 需要设置 cmake_file_name="Qt6" 和 cmake_target_name="Qt6::Core" 以匹配 Qt6 的 cmake target
---

**编译结束**: 2026-08-06 04:51
**最终状态**: built
