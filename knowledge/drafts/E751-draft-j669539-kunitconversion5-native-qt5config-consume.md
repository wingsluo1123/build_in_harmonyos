# E751：KF5 链消费 qt5-qtbase 原生 Qt5Config——cmake_find_mode=none + conan_cmakedeps_paths.cmake 手工接线

## 错误特征

```
CMake Error: Could not find a package configuration file provided by "Qt5"      ← 小写生成物遮蔽/寻址失败
CMake Error at */Qt5Core/Qt5CoreConfig.cmake:14 (message):
  The imported target "Qt5::Core" references the file
  ".../p/../b//mkspecs/linux-clang" but this file does not exist.               ← mkspecs 硬编码构建树路径
AUTOMOC: no moc executable found                                                ← CMakeDeps 不导出 Qt 工具
```

## 根因

KF5 系列（kunitconversion5/ki18n5 等）上游 CMake 写死 `find_package(Qt5 CONFIG REQUIRED Core Network)` 与 Qt5Test，需要 qt5-qtbase 包内**原生聚合 Qt5Config**（大写、组件齐全、带 imported target/mkspecs 语义）。四个缺口：

1. **遮蔽**：CMakeDeps 默认生成小写 qt5-qtbase-config.cmake 系生成物，遮蔽原生 config；
2. **寻址**：find_mode=none 后 prefix 不再自动注入，`find_package(Qt5)` 无处寻址；
3. **工具**：ECM/KDECMakeSettings 开 AUTOMOC，但 CMakeDeps 不导出 Qt5::moc/rcc；
4. **mkspecs**：Qt5CoreConfigExtrasMkspecDir.cmake 硬编码 `<pkg>/../b/mkspecs/linux-clang`（原构建树路径），打包缓存条目从未有构建树。

## 解法（四步组合，kitemviews5/kconfig5 先例）

**1. 抑制遮蔽**——generate() 关掉 CMakeDeps 对原生 config 依赖的生成：

```python
deps = CMakeDeps(self)
deps.set_property("qt5-qtbase", "cmake_find_mode", "none")
deps.set_property("ki18n5", "cmake_find_mode", "none")
deps.generate()
```

**2. 手工接线 prefix**——写 `conan_cmakedeps_paths.cmake`（tc.generate() 后追加，CMakeDeps toolchain 会 include 它）：

```python
lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
qt_pkg = qt5.package_folder
lines.append('list(PREPEND CMAKE_PREFIX_PATH "{}")'.format(qt_pkg))
lines.append('list(PREPEND CMAKE_PREFIX_PATH "{}/lib/cmake")'.format(qt_pkg))
lines.append('list(PREPEND CMAKE_LIBRARY_PATH "{}/lib")'.format(qt_pkg))
lines.append('list(PREPEND CMAKE_INCLUDE_PATH "{}/include")'.format(qt_pkg))
# ki18n5 自装 KF5I18nConfig.cmake（find_dependency Qt5Core）同法接 prefix；
# ECM 是 build-context 依赖：share/ECM/cmake 接入 CMAKE_MODULE_PATH+CMAKE_PREFIX_PATH
```

**3. 工具注入**——tc.variables 显式指 qt bin：

```python
for tool, cmake_var in (("moc", "CMAKE_AUTOMOC_EXECUTABLE"),
                        ("rcc", "CMAKE_AUTORCC_EXECUTABLE")):
    tc.variables[cmake_var] = os.path.join(qt5.package_folder, "bin", tool)
```

**4. mkspecs 兼容树**——把包内 mkspecs 整树拷到 Qt5CoreConfigExtras 预期位置：

```python
source = os.path.join(qt_package_folder, "mkspecs")
expected = os.path.join(os.path.dirname(qt_package_folder), "b", "mkspecs")
shutil.copytree(source, expected, dirs_exist_ok=True)
```

附加：`CMAKE_SYSTEM_NAME=Linux` 双覆盖（主配方+test_package）保 ECM 注册上游 ctest 与 POSIX rpath；`KF_SKIP_PO_PROCESSING=ON` + `GETTEXT_MSGFMT_EXECUTABLE` 显式注入（kpeople5 先例）规避沙箱 msgfmt 缺失。

## 降级方案

不用 find_mode=none 时：可让 CMakeDeps 正常生成并用 `tc.variables["Qt5_DIR"]` 显式指原生 Qt5Config 绝对路径——但小写生成物仍可能被部分 find_dependency 命中，稳定性差；或自写聚合 shim Qt5Config 转发到组件 config（维护成本高）。find_mode=none + paths 文件接线是 KF5 链最干净方案。

## 实证

kunitconversion5 5.116.0（PR !14840，j669539）：`find_package(Qt5 CONFIG REQUIRED Core Network)` + autotests Qt5Test 全解析；CTest 4/4（100% tests passed）；test_package 14/14。依赖组合：qt5-qtbase/5.15.2.2 + ki18n5/5.116.0 + ecm/6.26.0（tool_requires）。先例：kitemviews5 / kconfig5。
