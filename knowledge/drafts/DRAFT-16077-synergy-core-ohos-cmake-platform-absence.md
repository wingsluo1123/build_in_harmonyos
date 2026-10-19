# DRAFT-16077-synergy-core-ohos-cmake-platform-absence

## 症状（可复现）
synergy-core 1.21.4 在 OHOS aarch64 交叉编译时，配置/编译期两类问题：
```
# 配置期：X11 探测、XWindows 平台源、Unix arch 源全部被跳过（UNIX 变量为空）
# 编译期：
error: no member named 'partial_sort' in namespace 'std::ranges'
fatal error: 'make_shared' for array types (P0970) unsupported
error: use of undeclared identifier 'pthread_setcancelstate'
using value_type = Container::value_type;  // clang 15 需 typename（P0634 未覆盖该位置）
```

## 根因
1. **OHOS conan 工具链设 `CMAKE_SYSTEM_NAME=HarmonyOS`，但 CMake 无 HarmonyOS 平台模块** → `UNIX` 变量为空 → 所有 Linux 分支（X11 探测、`XWindows*` 平台源、Unix arch 源）被跳过。
2. **clang 15 + libc++ 算法缺口**：缺 `std::ranges::partial_sort/find/fill/find_if/for_each`；缺 P0970（`make_shared` 数组）；`pthread_setcancelstate/type` 未声明（OHOS libc POSIX cancellation 缺失）。
3. **cppstd 通道**：profile 固定 `cppstd=17`，上游需 C++20；仅通过 toolchain 变量提升无效——OHOS toolchain 在 `CMAKE_CXX_FLAGS` 注入之后追加 `-std=c++17`，尾随标志获胜。

## 已尝试方案
- ❌ 仅 toolchain 变量设 `CMAKE_CXX_STANDARD=20`：编译行仍 `-std=c++17`（尾随获胜）。
- ✅ `configure()` 设 `settings.compiler.cppstd=20`：C++20 生效。
- ✅ libc++15 兼容补丁族：`std::ranges` 算法全量替换为迭代器对经典算法、`make_shared` 数组改 `new[]`+value-init+数组删除器、pthread cancellation 改协作式取消。
- ✅ Linux 平台语义桥接 + `BUILD_X11_SUPPORT=ON` 对接 conan X11 客户端库（barrier/2.4.0 同源先例）。

## 最终方案
1. `settings.compiler.cppstd=20`（configure 层）。
2. `BUILD_X11_SUPPORT=ON` + `QT_VERSION_OVERRIDE=5.15`（Qt5→Qt6 别名桥由上游 `Libraries.cmake` 提供）。
3. 打 clang15/libc++ 兼容补丁族（16 个补丁）：ranges→迭代器对、P0970、pthread、`typename` 补丁、Qt Test 随 GUI 裁剪门控。
4. AUTOMOC 工具路径注入（`CMAKE_AUTOMOC_EXECUTABLE`）+ `LD_LIBRARY_PATH` 解析 `libc++_shared.so`。

## 适用范围 / 反例 / 解除条件
- 适用：CMake 无 OHOS 平台模块（UNIX 空）的所有老 CMake 项目 + clang15/libc++ 目标。
- 反例：仅设 toolchain 变量提 cppstd 无效（尾随 `-std=c++17` 获胜，本包实测）。
- 解除条件：CMake 官方补 HarmonyOS 平台模块 / libc++ 补齐 ranges 与 P0970。

## 查重与新增价值
- 查重结论：E431/E432、DRAFT-8945-botan3、DRAFT-332-openrct2 记录了 clang15/libc++20 部分兼容手法，但未覆盖「CMake 无 OHOS 平台模块致 UNIX 空」这一构建系统层根因，也未覆盖 cppstd 提升通道（toolchain 变量无效）机理。
- 新增价值：构建系统组合方案（平台语义桥接 + 选项门控）+ 测试形态调整（Qt Test 随 GUI 裁剪）双触发器。

## 触发实例
- synergy-core/1.21.4 @ HarmonyOS PC（conan + CMake + clang 15 OHOS），2026-10-16，PR #16077。
