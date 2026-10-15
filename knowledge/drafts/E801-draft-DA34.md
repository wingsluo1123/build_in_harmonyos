# E801 — qtbase(cmake_find_mode=none) 的消费侧映射：find_dependency(qtbase)/qtbase::qtbase 悬空

## 错误特征

```
CMake Error at .../CMakeFindDependencyMacro.cmake:78 (find_package):
  By not providing "Findqtbase.cmake" in CMAKE_MODULE_PATH this project has
  asked CMake to find a package configuration file provided by "qtbase"
Call Stack (most recent call first):
  .../<pkg>-config.cmake:24 (find_dependency)
```
或生成阶段：
```
The link interface of target "<pkg>_DEPS_TARGET" contains:
    qtbase::qtbase
  but the target was not found.
```
另：自写 `conan_cmakedeps_paths.cmake` 后 `find_package(libxcb)` 找不到配置。

## 触发条件

- 构建系统: cmake + Conan CMakeDeps
- 阶段: configure / generate（消费方 `find_package(<本包>)`）
- 依赖特征: 依赖 qtbase（其 recipe 声明 `cmake_find_mode="none"`），且本包需要发布
  给下游消费

## 根因分析

qtbase 自带完整可重定位的 `Qt6Config.cmake`，其 recipe 因此设
`cmake_find_mode="none"`，CMakeDeps 不为其生成配置。但它仍把 qtbase 写入消费包的
`<pkg>_FIND_DEPENDENCY_NAMES` 与 `<pkg>_DEPS_TARGET`；而 `get_cmake_package_name`
在依赖未设 `cmake_file_name` 时回退为裸包名 `qtbase`，于是：

1. `<pkg>-config.cmake` 里出现 `find_dependency(qtbase)` —— 无对应配置文件，FATAL；
2. 链接接口出现不存在的 `qtbase::qtbase`。

此外，配方自写 `conan_cmakedeps_paths.cmake` 时，`CMakeToolchain` 会**跳过**自身的
`find_paths` 块，生成器目录不再进入 `CMAKE_PREFIX_PATH`/`CMAKE_MODULE_PATH`，
`find_package(libxcb)` 等 CMakeDeps 配置随之找不到。

## 解决方案

### 推荐方案

在消费方 `generate()` 里对 qtbase 设 CMakeDeps 属性，映射到真实存在的 Qt6
配置与目标：

```python
cmake_deps = CMakeDeps(self)
cmake_deps.set_property("qtbase", "cmake_find_mode", "none")            # 不生成 qtbase 配置
cmake_deps.set_property("qtbase", "cmake_file_name", "Qt6")             # find_dependency(Qt6)
cmake_deps.set_property("qtbase", "cmake_target_name", "Qt6::Widgets")  # 真实目标
cmake_deps.generate()
```

- `Qt6::Widgets` 传递带出 `Qt6::Gui`/`Qt6::Core`；
- 生成的 `foreach` 由 `if(NOT Qt6_FOUND)` 守卫，故消费方先
  `find_package(Qt6 ...)` 时该查找被整体短路；
- 自写 paths 文件时补：
  `list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")` 与
  `list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")`。

同款做法见仓库内 libfm-qt / pcmanfm-qt。

### 禁止做法

- ❌ 忽略 `find_dependency(qtbase)` 失败。
- ❌ 手工修改生成器里的 `.cmake` 文件（每次 CMakeDeps 生成都会覆盖）。

## 验证

```bash
conan create <pkg> -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 2>&1 \
  | grep -E 'Findqtbase|qtbase::qtbase'
# 无输出即修复
```

## 关联条目

- 相关: E322（cmake_find_mode=none 目标桥接，grpc/protobuf 变体）
- 实证: qt-advanced-docking-system 4.5.0（test_package 消费侧）
