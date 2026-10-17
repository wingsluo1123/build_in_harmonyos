# lsp-r3d-iface

## 简介

lsp-r3d-iface 是 [lsp-plugins](https://github.com/lsp-plugins) 项目的 3D 渲染后端
接口层，定义 `backend_t`（`init_window`/`init_offscreen`/`locate`/`draw` 等纯 C
函数指针表）、`factory_t`（后端元信息查询与实例构造）、`backend_metadata_t`
（后端能力声明：窗口句柄类型、像素格式、矩阵/光照/图元枚举），以及
`builtin.h` 的 `Factory` 自动注册机制（`LSP_R3D_BUILTIN_FACTORY` 静态注册 +
`Factory::enumerate` 顺序遍历）。各具体后端（GLX、Vulkan、…）都实现这套接口。

## OHOS 适配

- **构建系统**：上游自研 make 系统（`make config` → `make` → `make install`）
- **适配方式**：本包源码 **零补丁**。上游 make 按 `uname -s` 探测平台，
  OpenHarmony PC 返回 "HarmonyOS"（上游不识别，落入 Unknown 分支），配方构建时
  显式传 `PLATFORM=Linux`；OHOS aarch64 目标（-march=armv8-a+asimd）与上游
  Linux 路径一致，源码无 `#ifdef` 平台差异。
- **依赖处理**：上游把 `lsp-common-lib`（生产）与 `lsp-test-fw`（测试）按
  `*TYPE=src` **内嵌编译**（`-D<NAME>_BUILTIN`，目标码并入本包静态库），靠
  `make fetch` git clone 取源码。配方改为由 conandata.yml 按上游 pin 版本提供
  tarball、`source()` 预置到 `modules/`，构建完全离线可复现。
- **内嵌依赖的移植补丁**：预置的 lsp-common-lib 与独立版同样缺 GNU `qsort_r`
  （musl libc），补丁在 `patches/modules/`（故意不在 `patches/` 顶层，原因见
  notes.md「注意事项」），由配方预置后应用。
- **Conan 依赖**：`lsp-common-lib/1.0.49@ohpcd/stable` +
  `transitive_headers=True`——本包公共头引用它的头文件，消费者必须能取到。
  注意该依赖需先发布到制品仓（R36）。
- **交付物**：`liblsp-r3d-iface-1.0.31.a`（含内嵌的 lsp-common-lib 目标码）+
  `lib/pkgconfig/lsp-r3d-iface.pc` + 头文件 `include/lsp-plug.in/r3d/iface/**`；
  `shared=False`（默认）仅静态库，`shared=True` 时 .so 自签名。
- **版本**：1.0.31（上游 tag）

## 依赖

- `lsp-common-lib 1.0.49`（头文件传递；目标码内嵌）
- 构建期源码：`lsp-test-fw 1.0.35`（仅上游测试，内嵌编译，不进生产包）

## 功能验证

```bash
# 上游测试可执行文件（上游 src/test 无用例，注册数为 0）
./.build/target/lsp-r3d-iface/lsp-r3d-iface-test      # exit 0，0 个用例

# 消费者测试（test_package，9 项断言）
./test_lsp-r3d-iface
#   lsp-r3d-iface 1.0.31
#   consumer checks passed
```

本机验证记录：`conan create` 通过；`conan-verify` G0–G4 PASS；消费者测试覆盖
`Factory` 注册/枚举、`factory_t` 函数指针表、注册链表遍历与枚举布局。

## 参考

- 上游仓库: https://github.com/lsp-plugins/lsp-r3d-iface
- License: LGPL-3.0-or-later
