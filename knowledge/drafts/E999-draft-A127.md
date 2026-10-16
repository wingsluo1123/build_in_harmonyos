# E999 — libindi 2.x Property API 迁移

## 错误现象

适配 indi-eqmod 1.0-20230126190232（2023-01 快照）到 libindi 2.2.2.1 时出现：

```
eqmodbase.cpp:269:35: error: no member named 'nsp' in 'INDI::PropertySwitch'
eqmodbase.cpp:194:26: error: 'operator&' is a protected member of 'INDI::PropertyBasic<_INumber>'
eqmodbase.cpp:448:28: error: no member named 'initGuiderProperties' in 'INDI::GuiderInterface'
eqmodbase.cpp:106:8: error: constructor for 'EQMod' must explicitly initialize the base class
                     'INDI::GuiderInterface' which does not have a default constructor
scope-limits.cpp:441:44: error: use of undeclared identifier 'timestamp'
defaultdevice.h:334:97: error: no type named 'any' in namespace 'std'
FindINDI.cmake:220: message: failed to detect INDI version
```

## 根因

1. **API 漂移**：libindi 2.0 起 Property 从底层结构（INumberVectorProperty*）抽象为
   `INDI::PropertyBasic<T>` 包装类。`operator&` 变 protected、底层成员（.sp/.nsp/.name/.s）
   需通过 `operator->`（backward-compat 宏启用时可用）访问。
2. **方法改名**：`initGuiderProperties(dev,grp)` → `initProperties(grp)`（protected）、
   `processGuiderProperties(...)` → `processNumber(dev,...)`、`timestamp()` → `indi_timestamp()`。
3. **构造器变更**：`INDI::GuiderInterface` 不再有默认构造器，需 `GuiderInterface(DefaultDevice*)`，
   派生类构造器必须显式初始化。
4. **C++ 标准**：libindi 2.2.x 头文件用 std::any（C++17），旧项目 CMakeCommon.cmake 强制 C++14。
5. **CMake 版本**：cmake_minimum_required(3.0) 与 CMake>=4 冲突，需 CMAKE_POLICY_VERSION_MINIMUM=3.5。
6. **版本检测**：FindINDI.cmake 正则 `.*INDI_VERSION ([0-9]+)...` 无法匹配
   `#define INDI_VERSION "2.2.2"`（带引号）。

## 修复方案

1. conanfile.py generate():
   - `CMAKE_SYSTEM_NAME=Linux` + `CMAKE_SYSTEM_PROCESSOR=aarch64`（OHOS 伪装 Linux）
   - `CMAKE_POLICY_VERSION_MINIMUM=3.5`
   - `CMAKE_CXX_STANDARD=17` + `REQUIRED=ON`
   - 自定义 Block 强制 `CMAKE_FIND_PACKAGE_PREFER_CONFIG OFF`（让项目自带 Find*.cmake 生效）
2. patch FindINDI.cmake 版本正则兼容引号。
3. 源码 API 迁移（见 .kv rec_approach 的 8 点），充分利用 backward-compat 的 operator->。
4. link c++/c++abi（OHOS libc++，libindi 2.2.2.1 配方同款）。

## 验证

- conan-verify G0-G4+L2/L4/L5 全 PASS
- W3 本地 CI（conan create 干净构建）exit_code=0
- 4 个驱动二进制 arm64 ELF 生成成功

## 关联

- E092（CMake 不识别 OHOS → CMAKE_SYSTEM_NAME=Linux）
- E515（refresh-patch git 风格补丁需 -p1，apply_conandata_patches strip）