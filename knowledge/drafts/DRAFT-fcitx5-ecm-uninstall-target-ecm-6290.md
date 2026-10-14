# DRAFT: include(ECMUninstallTarget) 需 ecm_uninstall.cmake.in → extra-cmake-modules 须 6.29.0+

## 现象

CMake configure 阶段（OHOS conan 配方，tool_requires extra-cmake-modules/6.19.0）：

```
CMake Error: File <ECM>/modules/ecm_uninstall.cmake.in does not exist.
CMake Error at <ECM>/modules/ECMUninstallTarget.cmake:39 (configure_file):
  configure_file Problem configuring file
```

## 根因

上游顶层 CMakeLists `include(ECMUninstallTarget)` 时，该模块 configure_file 引用
同目录的 `ecm_uninstall.cmake.in` 模板。extra-cmake-modules 6.19.0 的 conan 包只
打包了 `*.cmake` 模块，未包含 `.cmake.in` 模板；6.29.0 包含。fcitx5-utils 5.1.13
的 wrapper 构建根不含 `include(ECMUninstallTarget)`，因此 6.19.0 可用且已交付；
fcitx5 顶层直接 include 时必须 6.29.0+。

## 解决方案

```python
def requirements(self):
    self.tool_requires("extra-cmake-modules/6.29.0")
```

## 验证

- extra-cmake-modules/6.19.0 → configure 报 ecm_uninstall.cmake.in 缺失；
- 6.29.0 → configure/conan create/W3 build_and_test 全 pass（fcitx5/5.1.14 实测）。

## 适用边界

所有顶层 `include(ECMUninstallTarget)` 的 KDE/ECM 系 CMake 库，以 conan
extra-cmake-modules 为 tool_requires；与 ECM 版本差异相关的构建期依赖选择。

## 相关条目

- DRAFT-13796-qqc2-breeze-style-6.7.5-kf6-ecm-cmakedeps-bridge