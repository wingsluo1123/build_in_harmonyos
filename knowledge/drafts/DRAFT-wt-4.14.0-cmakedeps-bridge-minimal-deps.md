# DRAFT-wt-4.14.0-cmakedeps-bridge-minimal-deps

## 症状（可复现）
Wt(emweb) 4.14.0 在 Conan2 + CMakeDeps + OHOS aarch64 适配时，三类构建期问题：
```
CMake Error at cmake/WtFindBoost.txt: Could NOT find Boost (missing: program_options thread)
```
以及可选组件（PNG/GLEW/OpenGL/HPDF/Asciidoctor 等）被误查找致配置失败；上游 testsuite 依赖 Wt::Test harness + 网络服务场景，CI 沙箱不可构建。

## 根因
Wt 4.x 构建系统三处非标准行为：
1. 自带 `cmake/WtFindBoost.txt` 包装 `find_package(Boost 1.66 COMPONENTS program_options thread)`，命中后转为 `Boost::<comp>` IMPORTED 目标——需与 CMakeDeps 生成的 BoostConfig 桥接。
2. Boost>=1.69 移除独立 `filesystem` 组件（并入 system），Wt 默认仍查找它 → 查找失败。
3. 上游 testsuite 依赖随 `LIBWTTEST` 构建的 Wt::Test harness 和起监听端口的网络服务场景，OHOS CI 沙箱不可行。

## 已尝试方案
- ❌ 直接 `find_package(Boost)` 绕过 Wt 包装：丢失 `Boost::<comp>` 转换，Wt 目标链接失败。
- ✅ 保留 WtFindBoost 包装 + CMakeDeps 桥接 + `WT_CPP17_FILESYSTEM_IMPLEMENTATION=std` 绕开 filesystem 组件：配置通过。
- ✅ 最小依赖面裁剪 + `CMAKE_DISABLE_FIND_PACKAGE_*` 阻断可选查找：配置通过、编译通过。

## 最终方案
conan 配方 build()：
```python
cmake.configure(variables={
    'WT_CPP17_FILESYSTEM_IMPLEMENTATION': 'std',
    'BUILD_TESTS': 'OFF', 'LIBWTTEST': 'OFF', 'LIBWTDBO': 'OFF',
    'HARU': 'OFF', 'PANGO': 'OFF', 'SQLITE': 'OFF', 'POSTGRES': 'OFF',
    'FIREBIRD': 'OFF', 'MYSQL': 'OFF', 'OPENGL': 'OFF', 'UNWIND': 'OFF',
    'SAML': 'OFF',
    'CMAKE_DISABLE_FIND_PACKAGE_PNG': 'ON',
    'CMAKE_DISABLE_FIND_PACKAGE_GLEW': 'ON',
    'CMAKE_DISABLE_FIND_PACKAGE_OpenGL': 'ON',
    'CMAKE_DISABLE_FIND_PACKAGE_HPDF': 'ON',
    'CMAKE_DISABLE_FIND_PACKAGE_Asciidoctor': 'ON',
})
```
测试替代：test_package 端到端——真实 `WServer` + `wthttp` 连接器在 127.0.0.1 起服务，socket 级取页断言 HTTP 状态行 + 应用标记。

## 适用范围 / 反例 / 解除条件
- 适用：Wt 4.x + Conan2 CMakeDeps + Boost>=1.69；核心机理=自带 Find 包装与 CMakeDeps IMPORTED 目标桥接 + Boost 组件面按 1.69 后语义修正。
- 反例：直接 find_package(Boost) 不带 Wt 包装会丢 `Boost::<comp>` 转换。
- 解除条件：上游升级 Boost 组件声明或弃用自带 Find 包装后可移除。

## 查重与新增价值
- 查重结论：knowledge/ 与 worktree drafts 中无 WtFindBoost/emweb/wt-4.14 相关条目（首次申报）。
- 新增价值：构建系统组合方案（CMakeDeps 桥接 + 选项裁剪）+ 测试形态调整（无 Wt::Test 的 socket 级 e2e 替代）双触发器命中。

## 触发实例
- wt/4.14.0 @ HarmonyOS PC（conan + CMake + clang 15 OHOS），2026-10-16，PR #15480。
