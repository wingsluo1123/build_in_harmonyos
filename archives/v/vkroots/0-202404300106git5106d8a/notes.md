# vkroots 0-202404300106git5106d8a 适配笔记

## 编译环境

- 构建系统: meson（上游）；本包为 **header-only**，配方无编译阶段
- 编译日期: 2026-10-14
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang++`，target `aarch64-unknown-linux-ohos`）
- C++ 标准: **C++20**（上游 meson default_options `cpp_std=c++20`；profile 默认 17，需显式提升）
- 状态: built

## 编译步骤

上游为 header-only，配方只需安装头文件：

```bash
# 源码固定到 commit 5106d8a（见下「问题 1」：不可用 main）
conan create . --user=ohpcd --channel=stable \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# → package(): Packaged 1 '.h' file: vkroots.h
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 用上游 **main** 编译测试时失败 5 处：`no template named 'format_string' in namespace 'std'` / `no member named 'format' in namespace 'std'` / `no member named 'any_of' in namespace 'std::ranges'` | main 已使用 `std::format` / `std::format_string` / `std::ranges::any_of`，而 **OHOS 工具链 libc++ 15 不含 `std::format`** | **锁定提交 `5106d8a`**（本任务版本 0-202404300106git5106d8a 对应的 2024-04-30 快照，实测其中这些用法出现 0 次） |
| 2 | 消费者编译报 `vkroots.h:7:10: fatal error: 'vulkan/vk_layer.h' file not found` | ①OHOS SDK sysroot 只有 `vulkan.h`/`vulkan_core.h`/`vulkan_ohos.h`，**无 `vk_layer.h`**；②`vulkan-headers` 的 `package_type = "build-scripts"`，Conan 2.29 据此自动置该依赖 `visible=False`，导致 `cpp_info.requires` 校验报 `... is not a a direct requirement of the recipe` | 在 `requirements()` 显式 `self.requires("vulkan-headers/vulkan-sdk-1.4.357.0", visible=True)`，`cpp_info.requires` 用 `"vulkan-headers::vulkan-headers"`（知识库既有条目 **E545** 已记录该根因） |
| 3 | 上一步修复后 CMake 已声明 `vulkan-headers::vulkan-headers` 目标，仍报同一缺头文件 | `vulkan-headers` 的 `package_info()` 只打印 `CPATH=...`，**不通过 cpp_info 导出 include 目录**（实测 `vulkan-headers_INCLUDE_DIRS_RELEASE` 为空串） | 在自身 `package_info()` 中显式补上 `os.path.join(self.dependencies["vulkan-headers"].package_folder, "include")` |
| 4 | `-std=c++17`（profile 默认）下头文件语法不兼容 | 上游要求 C++20 | `package_info()` 中 `self.cpp_info.cxxflags = ["-std=c++20"]` 向下游传递 |
| 5 | 测试断言误判：期望产物导出 `vkGetInstanceProcAddr`/`vkGetDeviceProcAddr` | vkroots 采用 **Vulkan v2 协商接口**，这两个过程地址是**经协商结构体交回的指针**，不是动态符号 | 断言改为按实测导出的 `vkNegotiateLoaderLayerInterfaceVersion` 判定 |
| 6 | **CI 首次运行失败**（PR #15686 / build #91111 / worker `OpenHarmonyPCDeveloper-CI-014`）：`dlopen FAILED: Error loading shared library .../libvkroots_consumer_layer.so: Permission denied` | 产物**已经** `binary-sign-tool` 成功自签名，但该 worker 的安全策略仍拒绝 dlopen 本地新构建的共享库（与 E054/E374 同类，属平台策略层限制，代码不可修复） | **改为可执行文件形式的端到端用例**（`negotiate_main.cpp` → `vkroots_negotiate_e2e`）：把 layer 定义与协商调用放在同一可执行文件内，进程内直接调用 `vkNegotiateLoaderLayerInterfaceVersion`，**不依赖 dlopen / loader / GPU**，故本机与 CI worker 均可实跑；dlopen 那条路径整段移除，测试不再有任何环境依赖断言 |
| 7 | 自造假失败：`readelf -Ws … \| grep -qF …` 在 `set -o pipefail` 下被判失败 | `grep -q` 命中即退出并关闭管道 → `readelf` 收到 SIGPIPE 返回非零 → pipefail 使整条管道失败 | 改为「先把符号表存入变量 + shell 内建 `case` 匹配」，不经外部进程、不建管道 |

> 问题 2、3 可复用：凡是「依赖包的 package_type 为 build-scripts」或「公开头文件 include 了他人头文件」的场景都会遇到。
> 问题 6 可复用：**需要验证"可加载产物"的 test_package，若依赖 dlopen 外部 .so，在 CI worker 上很可能被安全策略拒绝**；
> 更稳的做法是把被测逻辑编进**可执行文件**在进程内实跑（同仓库 `vkfft` 的 test_package 即此形态）。
> 问题 7 可复用：`set -o pipefail` 与 `cmd | grep -q` 组合会因 SIGPIPE 产生假失败。

## 源码修改

**无 patches/**。本包未修改任何上游源码；上述全部处理都在 `conanfile.py` 的依赖声明与
`package_info()` 中完成，并通过 conandata.yml 固定源码提交。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| vulkan-headers | `vulkan-sdk-1.4.357.0` | 提供 `vulkan/vk_layer.h` 等头文件；**已发布在制品仓**。`visible=True`，并作为 `cpp_info.requires` 传给消费者 |

无运行期依赖（header-only，不产出库文件）。

## 上游测试清点（R51 第一步：清点留证）

**结论：上游没有测试套件（N=0）。**

1. 源码树无 `test/`、`tests/` 目录，`find <src> -iname "*test*"` 无命中；
2. `meson.build` 全文仅 `project()` + `declare_dependency()` + `override_dependency()` +
   `install_headers()` + `pkgconfig.generate()` —— 无 `executable()`、无 `test()`、无 `subdir('tests')`；
3. 上游仓库（含 main）同样不含测试目录。

因此本包测试覆盖 **100% 来自适配阶段补全（M=6）**，见 `test_package/MANIFEST.yml`。

## 验证结果

```bash
$ conan create . --user=ohpcd --channel=stable -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
...
[100%] Built target vkroots_negotiate_e2e
OK: 用例A：消费者 layer 编译成功，产物存在: libvkroots_consumer_layer.so (100736 字节)
OK: 用例B：端到端消费者可执行文件编译成功，产物存在: vkroots_negotiate_e2e (92608 字节)
OK: OHOS 运行时：两个产物均已自签名并置于 HMDFS 工作区（/data/service/hnp/bin/binary-sign-tool）
OK: 产物均为目标架构 arm64
OK: 用例A：layer 模块导出了 vkNegotiateLoaderLayerInterfaceVersion
OK: 用例B（端到端）：可执行文件实跑通过 —— [e2e] vkNegotiateLoaderLayerInterfaceVersion rc=0 (0=VK_SUCCESS)
-----------------------------------------
vkroots consumer test: PASS=6 FAIL=0
RESULT: PASSED
```

CI（PR #15686 / build #91349）：`Conan test_package` + `L0 门禁` + `L1 门禁` 全部通过。

产品包内容：`include/vkroots.h` + `licenses/{LICENSE,Apache-2.0.txt,LGPL-2.1-or-later.txt,MIT.txt}`。

## 交付物

| 文件 | 说明 |
|------|------|
| `include/vkroots.h` | 唯一的库文件（header-only） |
| `licenses/` | 上游许可证原文（vkroots.h 为 Apache-2.0 OR MIT；gen/ 脚本为 LGPL-2.1） |

## 注意事项

- **必须锁定提交 `5106d8a`**：改用 main 会在当前 OHOS 工具链上直接编译失败（libc++ 15 无 `std::format`）。
- **运行期边界（如实声明）**：本机与 CI 均无 Vulkan 驱动/ICD（无 `/dev/dri`、无 `/usr/share/vulkan/icd.d`），
  因此无法在真实 GPU 上验证 layer 的调用拦截行为。用例 B 通过「进程内跑通 loader 协商协议并断言
  `VK_SUCCESS` + 过程地址非空」完成运行期验证，更上层的真实渲染路径未覆盖。
- 上游 `sample/VkLayer_FROG_sample.cpp` 仅作 API 用法参考，未作为产物安装。
