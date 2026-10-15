# vkroots 0-202404300106git5106d8a — HarmonyOS PC 编译记录

## 概述

`vkroots` 是一个**单头文件**（header-only）框架，用于编写 Vulkan Layer —— 它把 Vulkan 官方
registry 的 XML 生成成完整的 dispatch 表与宏，让开发者只写「要拦截哪些调用」，其余样板由
`VKROOTS_DEFINE_LAYER_INTERFACES` 宏生成。

| 项目 | 值 |
|------|-----|
| 上游仓库 | https://github.com/Joshua-Ashton/vkroots |
| 锁定提交 | `5106d8a`（2024-04-30 快照，对应任务版本 0-202404300106git5106d8a） |
| 源码归档 | https://github.com/Joshua-Ashton/vkroots/archive/5106d8a.tar.gz |
| 许可证 | Apache-2.0 OR MIT（`vkroots.h` 及头文件）；`gen/` 脚本为 LGPL-2.1-or-later |
| 包类型 | header-only 库（不产出编译产物） |
| 编译状态 | ✅ 编译通过；消费者用例 **6/6 通过**（含 1 个端到端用例实跑） |

**编译环境**

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS PC / aarch64 |
| 编译器 | clang 15.0.4（`aarch64-unknown-linux-ohos`） |
| C++ 标准 | **C++20**（上游要求；OHOS profile 默认 17，配方用 `cpp_info.cxxflags` 向下游传递） |
| 依赖 | `vulkan-headers/vulkan-sdk-1.4.357.0`（已发布在制品仓） |

## ⚠️ 版本锁定（重要）

**不可改用上游 main。** main 已使用 `std::format` / `std::format_string` / `std::ranges::any_of`，
而 OHOS 工具链的 libc++ 15 **不含 `std::format`**，实测编译失败：

```
vkroots.h: error: no template named 'format_string' in namespace 'std'
vkroots.h: error: no member named 'format' in namespace 'std'
vkroots.h: error: no member named 'any_of' in namespace 'std::ranges'
```

本任务版本 `0-202404300106git5106d8a` 对应提交 `5106d8a`，该快照内无上述用法（出现 0 次），
故 `conandata.yml` 只写该 commit 的归档地址。

## 编译步骤

```bash
conan create . --user=ohpcd --channel=stable \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
```

header-only：配方无编译阶段，`package()` 仅安装 `vkroots.h` 与许可证。

## 依赖说明

| 依赖 | 是否需要 | 说明 |
|------|---------|------|
| `vulkan-headers/vulkan-sdk-1.4.357.0` | 必需 | OHOS SDK sysroot 只有 `vulkan.h`/`vulkan_core.h`/`vulkan_ohos.h`，**缺 `vk_layer.h`**；`vkroots.h` 直接 include 它，故必须引入上游 Vulkan-Headers |
| Vulkan loader / 驱动 | 不需要 | 本包为 header-only 框架，消费者用例可在**无 loader、无 GPU** 的情况下实跑（见下） |

## 消费者用例（test_package）

| 用例 | 形态 | 验证内容 |
|------|------|---------|
| A（集成） | 共享模块 `libvkroots_consumer_layer.so` | 用 vkroots 公开 API 编写最小 Vulkan layer 并编译为可加载模块；断言产物存在、目标架构 arm64、导出 `vkNegotiateLoaderLayerInterfaceVersion` |
| B（端到端，鸿蒙环境实跑） | 可执行文件 `vkroots_negotiate_e2e` | 在 OHOS 上**实际运行**：进程内构造 `VkNegotiateLayerInterface` 并调用 vkroots 生成的协商入口 `vkNegotiateLoaderLayerInterfaceVersion`，断言 `VK_SUCCESS` 且交回的 `pfnGetInstanceProcAddr` / `pfnGetDeviceProcAddr` 非空 |

> 用例 B 特意把 layer 定义与协商调用放在**同一可执行文件**内，因此不依赖 `dlopen`
> 外部 `.so`、Vulkan loader 或 GPU —— 这一点很关键：CI worker 的安全策略会以
> `Permission denied` 拒绝 dlopen 本地新构建的共享库，而本形态在本机与 CI 上都能实跑。

## 已知限制

- **无 Vulkan 驱动 / ICD**：本机与 CI 均无 `/dev/dri`、无 `/usr/share/vulkan/icd.d`；
  OHOS SDK 仅提供 `libvulkan.so` 桩。因此无法在真实 GPU 上验证 layer 的调用拦截行为。
  用例 B 已把「协商协议真实跑通」这一层验证到位；更上层的真实渲染/拦截路径未覆盖。
- 上游无测试套件（N=0），全部 6 条断言为适配阶段补全（见
  `0-202404300106git5106d8a/test_package/MANIFEST.yml`）。

## 验证结果

| 测试项 | 命令 | 结果 |
|--------|------|------|
| 包创建 | `conan create` | ✅ 成功（header-only，仅装头文件） |
| 用例 A 编译 | test_package（CMake，C++20） | ✅ `libvkroots_consumer_layer.so`（100736 字节） |
| 用例 B 编译 | 同上 | ✅ `vkroots_negotiate_e2e`（92608 字节） |
| 目标架构 | `file` | ✅ 两产物均为 ELF 64-bit LSB arm64 |
| 用例 A 入口点 | `readelf -Ws` | ✅ 导出 `vkNegotiateLoaderLayerInterfaceVersion` |
| **用例 B 端到端实跑** | `./vkroots_negotiate_e2e` | ✅ `[e2e] ... rc=0 (0=VK_SUCCESS)`，两个过程地址非空 |
| 消费者断言合计 | `test.sh` | ✅ **6/6 通过**（PASS=6 FAIL=0） |
| CI 流水线 | PR #15686 / build #91349 | ✅ `Conan test_package` + `L0 门禁` + `L1 门禁` 全通过 |
