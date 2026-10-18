# pkg_check_modules 的 `<PREFIX>_FOUND` 变量令 CMakeDeps 配置跳过 find_dependency

## 现象

一个同时用 pkg-config（`pkg_check_modules`）和 Conan `CMakeDeps` 的 CMake
工程，配置时报：

```
CMake Error: The link interface of target "boost_Boost_iostreams_DEPS_TARGET"
contains:
    ZLIB::ZLIB
but the target was not found.
Call Stack:
  BoostConfig.cmake:16 (include)
  CMakeLists.txt:131 (find_package)
```

## 根因

1. 工程先调用 `pkg_check_modules(ZLIB REQUIRED IMPORTED_TARGET zlib)`，
   这会设置普通变量 `ZLIB_FOUND=1`（以及 `PkgConfig::ZLIB` 目标）。
2. 随后 `find_package(Boost)` 命中 Conan `CMakeDeps` 生成的
   `BoostConfig.cmake`。该文件在 include 完 targets 之后，遍历
   `boost_FIND_DEPENDENCY_NAMES`（此处为 `ZLIB`）：
   ```cmake
   foreach(_DEPENDENCY ${boost_FIND_DEPENDENCY_NAMES})
     if(NOT ${_DEPENDENCY}_FOUND)      # ← ZLIB_FOUND 已为真，跳过
       find_dependency(${_DEPENDENCY} REQUIRED ${${_DEPENDENCY}_FIND_MODE})
     endif()
   endforeach()
   ```
3. 因为 `ZLIB_FOUND` 已被 pkg-config 置真，`find_dependency(ZLIB)` 被跳过，
   `ZLIBConfig.cmake` 从未被加载，`ZLIB::ZLIB` 目标不存在；而 Boost 的
   iostreams 组件（`boost_Boost_iostreams_DEPS_TARGET`）的
   `INTERFACE_LINK_LIBRARIES` 引用了 `ZLIB::ZLIB` → CMake generate 阶段
   报「target was not found」。

本质是 **pkg-config 前缀名与 CMake 包名同名**（`ZLIB`/`CURL`/`OpenSSL`/`EXPAT`）
造成的变量命名空间冲突。

## 修复

在 `find_package(Boost)` 之前显式按 config 模式加载 ZLIB，使 `ZLIB::ZLIB`
提前存在：

```cmake
set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)
# OHOS/Conan: pkg_check_modules(ZLIB ...) 已设置 ZLIB_FOUND，令 BoostConfig
# 跳过 find_dependency(ZLIB)；这里显式加载 config 模式的 ZLIB。
find_package(ZLIB CONFIG REQUIRED)
find_package(Boost 1.71 REQUIRED)
```

回退方案：`unset(ZLIB_FOUND)`（让 BoostConfig 自己 `find_dependency`）。

## 与既有条目的边界

- `E468`（PkgConfigDeps/PKG_CONFIG_PATH/generators_folder）讲的是 pkg-config
  文件搜索路径；`E480` 讲 autotools `PKG_CHECK_MODULES` 传递头。本条是
  **CMake/Conan 侧**：pkg-config 前缀变量与 CMakeDeps 依赖配置的
  `find_dependency` 守卫冲突，修法层位是「显式 config find」，与二者不同。

## 证据

- valhalla 3.8.2（任务 11598）：`pkg_check_modules(ZLIB REQUIRED ...)` 在
  `find_package(Boost 1.71 REQUIRED)` 之前；补丁 `0004` 插入
  `find_package(ZLIB CONFIG REQUIRED)` 后 configure 通过。
