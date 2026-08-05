# coreimage latest 适配笔记

## 编译环境
- 构建系统: cmake (原项目使用 qmake，创建 CMakeLists.txt)
- 编译日期: 2026-08-06
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: https://api.github.com/repos/rahmanshaber/coreimage/tarball/master
2. 应用 Qt6 兼容性补丁 (0001-qt6-compat.patch)
3. 应用 CMakeLists.txt 补丁 (0002-add-cmake-build.patch, 使用 conan 管理依赖)
4. conan create + conan test

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | QShortcut 修饰符组合报错 | Qt6 用 \| 替代 + | 修改为 Qt::ControlModifier \| Qt::Key_O |
| 2 | wheelEvent delta() 不存在 | Qt6 移除 delta() | 用 angleDelta().y() |
| 3 | mouseEvent globalPos() 不存在 | Qt6 移除 globalPos() | 用 globalPosition().toPoint() |
| 4 | pixmap() 返回类型改变 | Qt6 返回值不是指针 | 用 pixmap().isNull() 和 pixmap().size() |
| 5 | 原项目无 CMakeLists.txt | 只有 .pro 文件 | 创建 CMakeLists.txt 使用 conan 依赖 |

## 源码修改

- 0001-qt6-compat.patch: Qt6 API 兼容性修复 (coreimage.cpp)
- 0002-add-cmake-build.patch: 新增 CMakeLists.txt (使用 conan 管理的 cprime 和 Qt6)

## 依赖版本

- qtbase/6.11.1 (from ohpcd remote)
- libcprime/latest (adapted in this session, PR #4189)

## 验证结果

```bash
conan create archives/c/coreimage/latest -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# Tests pass
```

## 注意事项

- coreimage 是应用程序 (不是库)，构建产物是可执行文件
- 依赖 libcprime 需要先适配并发布 (PR #4189)
- CMakeLists.txt 使用 conan 管理的 find_package(cprime) 和 find_package(Qt6)

---

**编译结束**: 2026-08-06 05:00
**最终状态**: built
