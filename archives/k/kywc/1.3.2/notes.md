# kywc 1.3.2 适配笔记

## 版本与源码

- 上游项目：kylin-wayland-compositor（`https://gitee.com/openkylin/kylin-wayland-compositor`）
- 源码包：Debian pool 的 `kylin-wayland-compositor_1.3.2.orig.tar.xz`
  - gitee 仓库只有 `upstream/1.3.0`、`upstream/1.3.1` 两个 tag，1.3.2 是 Debian
    打包修订（源包名 `kylin-wayland-compositor`，二进制包 `libkywc1` /
    `libkywc1-dev` / `kylin-wayland-compositor`），故按 Debian pool 源取包
    （R39；units-filter / userinfo / uucpsend 先例）。
  - sha256（本地实测）：`d5169a9c943337d226c436d4b2cfa5107921a7f24d3cb2fbdcf5580d6eeb3e20`
- **版本号不一致说明**：orig tar 内 `meson.build` 仍写
  `version: '1.3.0'`（上游自己的发布疏漏），生成的 `kywc.pc` 也报
  `Version: 1.3.0`。源码内容即 Debian 1.3.2 版本；Conan ref 按任务卡登记为
  `kywc/1.3.2`。`ukui-quick` 的 `pkg_check_modules(... REQUIRED kywc)` 未带
  版本约束，不受影响。

## 为什么只构建 libkywc

`ukui-quick 4.22.0.1` 的 `modules/window-thumbnail/` 使用
`pkg_check_modules(... REQUIRED kywc)` 与 `#include <libkywc.h>`（Debian
Build-Depends `libkywc1-dev`），只需要客户端库 libkywc。

上游顶层 `meson.build` 无条件探测整套合成器依赖（wlroots-0.20、xcb、
wayland-server、xkbcommon、libdrm、libinput、pixman、json-c、libsystemd、
cairo/pango/pangocairo、librsvg、libjpeg、libpng、libudev、gbm、
libdisplay-info），这些在 OHOS 制品仓中均未发布。三个本地补丁把构建拆开：

| 补丁 | 作用 |
|---|---|
| `0001-meson-options-add-compositor-switch.patch` | `meson_options.txt` 新增 `compositor` 布尔开关，默认 `true`（保持上游完整构建行为）|
| `0002-meson-gate-compositor-and-keep-libkywc.patch` | 根 `meson.build` 用 `have_compositor` 门控全部合成器依赖探测，以及 `data`、`src`、`examples`、`tools`、`portal` 子目录与 `kylin-wlcom` 可执行文件；`protocols` 与 `libkywc` 子目录保持无条件构建 |
| `0003-libkywc-gate-buffer-helper.patch` | `libkywc/meson.build` 中仅供 examples/tools 使用的 buffer 辅助（egl/glesv2/wayland-egl/libpng）移入 `have_compositor and (have_examples or have_tools)` 门控，使 libkywc 本身只链接 wayland-client 与 libm |

补丁格式与验证：纯 unified diff（`--- a/` / `+++ b/` 两行头，无 `diff --git`）。
三个补丁按 conandata 顺序经 patch_ng `strip=1` 逐级应用全部成功；打补丁后的
源码树与设计目标树 `diff -r` 完全一致（逐字节）。

`-Dcompositor=false` 后仍会构建 `protocols/`：libkywc 的 4 个管理器协议
（kywc-capture / kywc-output / kywc-toplevel / kywc-workspace manager v1）
需要 `private-code` 与 `client-header` 产物；其余协议在 `protocols/meson.build`
里只是 `custom_target` 声明，未被任何目标引用时不会生成。

## 构建要点（OHOS）

- 构建系统：meson；依赖 `wayland/1.24.0`、`wayland-protocols/1.48`（均在
  ohpcd 已发布）。
- **静态 wayland-scanner**：HMDFS 禁止执行链接了缓存共享库的二进制，
  wayland 包自带 scanner 在设备上不可运行。`generate()` 从 wayland 1.24.0
  源码用 clang 编译一个只依赖 libc 的静态 scanner（expat 静态库来自 SDK
  `/data/service/hnp/expat.org/expat_2.7.3/lib/libexpat.a`，找不到时回退
  依赖包的 `lib/libexpat.a`），并把 generators 目录前置到 `PATH`，供
  `protocols/meson.build` 的 `find_program('wayland-scanner')` 解析
  （wayland-protocols/1.48 先例）。
- **wayland-protocols.pc 的 pkgdatadir**：`protocols/meson.build` 调用
  `wayland_protos.get_variable('pkgdatadir')`，而 PkgConfigDeps 生成的
  `.pc` 没有该变量。手写 `fixed_pkgconfig/wayland-protocols.pc`
  （`pkgdatadir=${prefix}/share/wayland-protocols`）并置顶
  `PKG_CONFIG_PATH`。
- **依赖 .pc 的可见性**：配方只用 MesonToolchain，不会自动生成依赖的
  `.pc`；`generate()` 遍历 host 依赖，把各自 `lib/pkgconfig` 追加到
  `PKG_CONFIG_PATH`（`package_folder` 为 None 的跳过——本图为 libffi）。
- **wayland-client.pc 的 Requires.private**：wayland 包产出的
  `wayland-client.pc` 带 `Requires.private: libffi`，而本构建不需要
  libffi 二进制（未安装），pkg-config 因私有依赖缺失拒绝输出 cflags。
  手写最小 `fixed_pkgconfig/wayland-client.pc`（仅 `-lwayland-client`）置顶；
  真实 wayland-client 客户端 API 不依赖 libffi。test_package 用同一手法，
  避免 PkgConfigDeps 的聚合 `wayland-client.pc` 把 cursor/egl/expat/xml2
  带进链接（OHOS 加载器拒绝 libwayland-cursor.so）。
- **ar/ranlib**：meson 子进程在 HMDFS 下解析不到 llvm-ar，注入
  `conan_meson_native.ini` 的 `[binaries]`（zix/serd/wayland 先例），同时
  导出 `AR`/`RANLIB` 环境变量。
- **签名**：`meson install` 会重写安装的 ELF（清空 build 树 RUNPATH），
  使链接期 `.codesign` 段失效；`package()` 用 `llvm-objcopy
  --remove-section .codesign` + `binary-sign-tool -selfSign 1` 重新签名
  （libinput/kpkpass 先例）。
- **SONAME 链接**：`libkywc.so.1` / `libkywc.so` 软链接若在安装时丢失，
  按 `libkywc.so.<ver>` 重建；文件系统拒绝 symlink 时回退为字节拷贝
  （libinput 先例）。
- meson 选项：`-Dcompositor=false -Dlibkywc=true -Dexamples=false
  -Dtools=false -Dportal=false -Dnls=disabled -Dlibunwind=disabled`.

## 上游测试清点（R51）

清点命令与结果（在 1.3.2 源码树内实测）：

```
$ find . -type d \( -name test -o -name tests -o -name autotests \)
（无输出）
$ grep -rn "^[^#]*\btest(" --include=meson.build .
（无输出）
$ grep -rn "add_test\|enable_testing\|ctest" --include=meson.build .
（无输出）
$ find . -name meson.build | wc -l
37
```

结论：**上游无测试套件**——没有 tests/ 目录，37 个 meson.build 中没有任何
`test()` 注册或 `add_test`/CTest 集成。`examples/ukui-effect-test.c` 是示例
程序（仅在 `examples=true` 时构建的演示），不是测试用例。因此上游测试实测
数量为 **N=0**，test_package 的消费者测试是唯一可执行验证。

## 消费者测试（test_package）

- 构建方式：CMake + `PkgConfigDeps`，用 `pkg_check_modules(kywc REQUIRED)`
  发现安装产物（与 ukui-quick 的 window-thumbnail 模块同一路径）；
  `wayland-client` 同样经 pkg-config 引入。
- `libwayland-server` 按路径显式链接：wayland 包同时提供
  `libwayland-cursor.so` / `libwayland-egl.so`，其 ELF 会被 OHOS 加载器
  拒绝，聚合目标会把它们带进来导致测试程序无法启动
  （plasma-wayland-protocols 先例）。
- 测试程序在进程内启动 Wayland 服务端（`wl_display_create` +
  `wl_display_add_socket_auto` + 服务线程），`XDG_RUNTIME_DIR` 优先选取
  `/data/storage/el2/base/tmp`、`/data/storage/el2/base/cache`（HMDFS
  `/storage` 上 AF_UNIX bind 返回 EPERM）。
- 用例：caps=0 生命周期（create 回调、display、fd、user data、迭代器、
  find 帮助函数、destroy 回调）、OUTPUT|TOPLEVEL|WORKSPACE 能力对无全局
  服务端的空迭代与 null-safe 销毁、`kywc_context_create_by_display` 非拥有
  语义、缺失 socket 返回 NULL、NULL 参数安全性。共 37 项检查，输出逐项
  `CHECK PASS/FAIL` 与 `TEST SUMMARY: N passed, M failed`，失败时退出码 1。
- OHOS 额外场景：`harmony_tests/private_signed_loader.py` 校验真实
  `.codesign` 段，把构建出的 ELF 复制到 `/data/storage/el2/base/cache`
  的私有 inode 后重跑整套用例。

## 真机验证

真机（OHOS aarch64 / clang 15 / conan 2.29.1）执行：

```
conan create . -pr:h=$HOME/bih/ci/conan/profiles/ohos-aarch64 \
  -pr:b=$HOME/bih/ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable -c tools.build:jobs=2
```

结果（rc=0）：

- 库构建与打包：成功，`kywc/1.3.2@ohpcd/stable` 二进制入本地缓存
- 消费者测试：`TEST SUMMARY: 37 passed, 0 failed`
- OHOS 私有 inode 重跑：`TEST SUMMARY: 37 passed, 0 failed`，
  `HARMONY_TEST_COUNT=1`、`HARMONY_TEST_PASS=1/1`，真实 `.codesign`
  段校验通过（`ACTUAL_SIGNED_ELF_SHA256=c9bdf279…`）
- 用例覆盖：caps=0 生命周期、OUTPUT|TOPLEVEL|WORKSPACE 对无全局服务端的
  空迭代与 null-safe 销毁、`kywc_context_create_by_display` 非拥有语义
  （销毁后调用方 display 仍可 `wl_display_roundtrip`，返回 2 个已派发
  事件、display error 0）、缺失 socket 返回 NULL、NULL 参数安全
- 上游测试 N=0（无测试套件），消费者测试是唯一可执行验证

## 交付物

- `lib/libkywc.so.1.3.0`（SONAME `libkywc.so.1`，含 `libkywc.so.1` /
  `libkywc.so` 链接）
- `include/libkywc.h`
- `lib/pkgconfig/kywc.pc`

## 注意事项

- 合成器本体（kylin-wlcom、portal、tools）未构建：依赖栈未在 OHOS 发布，
  且 ukui-quick 只消费 libkywc。`-Dcompositor=true` 仍是上游默认值，
  将来依赖齐备时可复用同一配方打开。
- `kywc.pc` 的 Version 是 1.3.0（见上），下游不要写 `>= 1.3.2` 的 pkg-config
  约束。
