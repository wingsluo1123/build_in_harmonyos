# vkroots 0-202404300106git5106d8a — 验证报告（HarmonyOS PC / aarch64）

- 源码 SHA-256：`37b77586e91f7ebee70380dcddd73bf01ae4acef1053e6be41d0485ede022422`
  （`vkroots-5106d8a.tar.gz`，锁定上游 commit `5106d8a` = 2024-04-30 快照）
- 工具链：clang 15.0.4，target `aarch64-unknown-linux-ohos`，libc++（C++20）
- 构建系统：meson（上游）；本包 **header-only**，配方无编译阶段
- 制品引用：`vkroots/0-202404300106git5106d8a@ohpcd/stable`

> 说明：`reports/*.log`、`.ci-result.json` 等为构建/CI 工具在工作机上生成的**运行时产物**，
> 按仓库 `.gitignore`（`reports/` 等）不入库；本报告以「实测值」形式记录其结论。

## 独立分母（Independent denominator）

| 测试层级 | 实测结果 | 证据（实测值） |
| --- | --- | --- |
| 上游官方测试套件 | **0 项**（上游无任何测试套件） | 源码树无 test/ 目录；meson.build 无 test()/executable()/subdir('tests') 注册；上游仓库（含 main）同样无测试目录 |
| 适配后补全的 test_package 断言 | **6/6 通过**（PASS=6 FAIL=0） | 开发机与 CI 均为全绿（CI：build #91349，`Conan test_package / L0 / L1` 全通过） |
| conan create 干净构建（含 test_package） | **通过** | `conan-verify` 报告 `Verdict: PASS`（G0 ✅ / G1 ✅ 全项） |
| W3 本地 CI 模拟（JC / L0–L5） | **通过**（`exit_code=0`，`Errors: 0`） | `.ci-result.json` → `log_sha256=0ea677670b726bbe7d3b501441d54bcc3d8a42d9a8627e82c1df254de5a20c63` |
| 用例 A 产物 | `libvkroots_consumer_layer.so`，100736 字节，`ELF ... arm64` | 断言 1 / 4 / 5 |
| 用例 B 产物 | `vkroots_negotiate_e2e`，92608 字节，实跑 `rc=0 (VK_SUCCESS)` | 断言 2 / 4 / 6 |

## 上游测试清点（R51 第一步）

**结论：上游没有任何测试套件（N=0）。** 三项独立证据：

1. 源码树无 `test/`、`tests/` 目录，`find <src> -iname "*test*"` 无命中；
2. `meson.build` 全文仅 `project()` + `declare_dependency()` + `override_dependency()` +
   `install_headers()` + `pkgconfig.generate()` —— 无 `executable()`、无 `test()`、无 `subdir('tests')`；
3. 上游仓库递归树查询（含 main 分支）测试相关路径数 = 0。

因此本包测试覆盖 **100% 来自适配阶段补全（M=6）**。

## 两个消费者用例（均为真实使用被测头文件，非纯断言）

### 用例 A（集成）：可加载的 Vulkan layer 模块

`test_layer.cpp` 用 vkroots 的公开 API（`VKROOTS_DEFINE_LAYER_INTERFACES`、
`vkroots::VkDeviceDispatch`、`vkroots::NoOverrides`）编写一个最小 layer，编译为
`libvkroots_consumer_layer.so`；含编译期版本宏 `static_assert`。
断言：产物存在（1）、目标架构 arm64（4）、导出 `vkNegotiateLoaderLayerInterfaceVersion`（5）。

### 用例 B（端到端，鸿蒙特有）：进程内真实跑通 layer 协商流程

`negotiate_main.cpp` 编译为可执行文件 `vkroots_negotiate_e2e`，在 OHOS 上**实际运行**：
构造 `VkNegotiateLayerInterface`（`sType=LAYER_NEGOTIATE_INTERFACE_STRUCT`、
`loaderLayerInterfaceVersion=2`）并调用 vkroots 生成的协商入口
`vkNegotiateLoaderLayerInterfaceVersion`，断言返回 `VK_SUCCESS` 且交回的
`pfnGetInstanceProcAddr` / `pfnGetDeviceProcAddr` 非空。

**该用例不需要 Vulkan loader / GPU / dlopen**，因此在本机与 CI worker 上都能实际执行
（这一点很关键：dlopen 本地新构建的 `.so` 会被 CI worker 安全策略以
`Permission denied` 拒绝，而本用例把 layer 定义与协商调用放在同一可执行文件内，绕开了该限制）。

## 断言明细（6 条，全部为硬断言）

| # | 断言 | 验证内容 |
| --- | --- | --- |
| 1 | 用例 A 产物存在 | 消费者 layer 编译成功（100736 字节） |
| 2 | 用例 B 产物存在 | 端到端可执行文件编译成功（92608 字节） |
| 3 | OHOS 运行时：两产物自签名并落位 HMDFS | 拷贝至 `$HOME/tmp` + `binary-sign-tool` 自签名（R7/E054/E374） |
| 4 | 产物均为目标架构 | `file` 判为 arm64 |
| 5 | 用例 A 导出 layer 入口点 | `readelf -Ws` 检出 `vkNegotiateLoaderLayerInterfaceVersion` |
| 6 | **用例 B 端到端实跑通过** | 运行可执行文件，输出 `[e2e] ... rc=0 (0=VK_SUCCESS)` 且退出码 0 |

## 测试环境限制（如实声明）

- **无 Vulkan 驱动 / ICD**：本机无 `/dev/dri`，无 `/usr/share/vulkan/icd.d`；OHOS SDK 仅提供
  `libvulkan.so` 桩。因此 **无法** 在真实 GPU 上验证 layer 的调用拦截行为。
- 用例 B 是在该限制下能做到的最强运行期验证：证明 vkroots 生成的 layer 接口在运行期
  确实可用（协商协议真实跑通），而不仅是"编译通过"。更上层的真实渲染/拦截路径未覆盖。
- 上游 `sample/VkLayer_FROG_sample.cpp` 仅作 API 用法参考，未安装为产物。

## 本报告未覆盖的范围

本报告不构成对正式 CI、代码检视或提交结果的认证——这些环节须以最终推送的 HEAD 为准。
