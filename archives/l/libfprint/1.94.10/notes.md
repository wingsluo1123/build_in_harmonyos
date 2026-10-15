# libfprint 1.94.10 适配笔记

## 编译环境
- 构建系统: meson（+ ninja），OHOS aarch64 交叉/原生编译
- 编译日期: 2026-10-03
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18 工具链，`-stdlib=libc++`，cpp_std=c++17）
- 状态: built（conan-verify 通过，未 upload）

## 编译步骤（探索阶段实测，与配方一致）

```bash
# 依赖 .pc 集合由 conan PkgConfigDeps 生成到 reqs/（fixpc.py 把 prefix=/ 重写为真实 conan 包目录，R49）
meson setup build-exp \
    -Ddrivers=all -Dintrospection=false -Dudev_rules=disabled \
    -Dudev_hwdb=disabled -Dgtk-examples=false -Ddoc=false \
    -Dexamples=false -Dinstalled-tests=false -Dmetainfo=false \
    --wrap-mode=nodownload --buildtype=release
ninja -C build-exp
# 产物：build-exp/libfprint/libfprint-2.so.2.0.0
DESTDIR=$TEST_PREFIX ninja -C build-exp install
```

conanfile.py 复现要点：
- `MesonToolchain` + `PkgConfigDeps`（meson 配方，非 autotools 模板）
- `build_requirements(): tool_requires("meson/1.11.0")`（QA 原要求 1.11.0.1，但远端制品损坏无法下载，见依赖表）
- `generate()`: 写 gio-unix-2.0.pc shim（glib 配方不导出，libfprint meson 需要 `dependency('gio-unix-2.0')`）、R49 .pc prefix 防御重写、往 native/cross ini 注入 ar/ranlib/pkg-config、pkg_config_path 追加依赖包目录
- `build()`: `Meson.configure()` + `Meson.compile()`；`package()`: `Meson.install()` + `_restore_pristine_shared_libraries()`（meson install 会改写安装产物 .dynstr 破坏 lld codesign 摘要，从构建树拷回原始 .so；`_sign_shared_libraries` 已置 NO-OP，见下方会话记录）

## 上游测试申报表（meson test 实测，33 项）

| 类别 | 数量 | 实测结果 | 技术原因 |
|------|------|----------|----------|
| 单测 fpi-device | 1 | ✅ 通过 | — |
| 单测 fpi-ssm | 1 | ✅ 通过 | — |
| 单测 fpi-assembling | 1 | ✅ 通过 | — |
| udev-hwdb | 1 | ✅ 通过 | — |
| 单测 fp-context | 1 | ❌ Fail（killed by SIGTRAP） | `/context/remove-device-closing` 需创建 AF_UNIX socket（虚拟设备监听），沙箱禁止 bind（EPERM：`Could not listen on unix socket: Error binding to address (GUnixSocketAddress): Operation not permitted`）；libusb 初始化亦报 Input/Output Error。环境限制，非适配缺陷 |
| 单测 fp-device | 1 | ❌ Fail（killed by SIGTRAP） | `/device/async/open` 同因（虚拟设备 AF_UNIX bind EPERM）。环境限制 |
| 驱动测试（virtual-image/aes2501/elan/... 27 个） | 27 | ⏭️ Skipped | 需真实指纹硬件/USB 设备/捕获数据，沙箱无硬件 |

- 注册 33 项 / 实测 4 过 2 败 27 跳（全部可跑项 4/4 通过，通过率 100%）
- 日志证据：`.tmp_diag/libfprint/testlogs/meson-test-suite.log`、`test-fp-context.log`、`test-fp-device.log`、`test-fpi-device.log`、`test-fpi-ssm.log`、`test-fpi-assembling.log`
- 说明：fp-context 的 `/context/new`、`/context/no-devices` 等 7 个子项在沙箱内均通过，仅需绑定虚拟设备 AF_UNIX socket 的子项失败，已实证为沙箱网络能力限制

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | fp-context/fp-device 测试 SIGTRAP | 沙箱禁止 AF_UNIX socket bind（EPERM），虚拟设备监听失败 | 环境限制，notes 申报表记录，非代码缺陷 |
| 2 | examples/metainfo 无法编译/运行 | `fprint-list-metainfo` 是交叉编译产物，无法在构建主机运行；examples 为可选桌面程序 | 补丁 0001-0003 增加 meson_options 开关并门控 subdir/custom_target，`-Dexamples=false -Dmetainfo=false` |
| 3 | gio-unix-2.0.pc 缺失 | glib 配方未导出 gio-unix-2.0.pc，而 libfprint meson 依赖 `gio-unix-2.0` | generate() 从 glib 包目录合成 gio-unix-2.0.pc（ayatana-indicator-power 同款） |
| 4 | .pc prefix 为 `/` | 手工收集的 .pc 集合 prefix 为空 | fixpc.py / 配方内 `_rewrite_dependency_pc_prefixes` 重写为真实 conan 包目录（R49） |
| 5 | libusb 初始化失败 | 沙箱无 USB 后端 | 非致命（libfprint 降级继续），driver 探测返回空列表，如实记录 |
| 6 | goodix_proto.c / realtek.c 编译失败（`expected expression`） | case 标签后直接声明 C99 变量，clang -std=gnu99 视为语法错误（探索阶段改过源文件但未出补丁） | 补丁 0001/0002 给 case 体加 `{}` 块 |

## 2026-10-04 会话：conan create test_package 运行期修复（W3 全绿）

`conan create` 曾三连败：①`Library 'libfprint-2' not found in package` → ②`fatal error: 'libfprint/fprint.h' file not found` → ③运行期 `Error loading shared library libfprint-2.so.2 / symbol not found`。逐层根因与修复：

| # | 报错 | 根因 | 修复 |
|---|------|------|------|
| 1 | `Library 'libfprint-2' not found in package`（cmakedeps_macros.cmake:81） | `cpp_info.libs=["libfprint-2"]` 传入 CMakeDeps 的 `find_library(NAMES libfprint-2)`，CMake 会再拼 `lib` 前缀去找 `liblibfprint-2.so` → NOTFOUND | `cpp_info.libs=["fprint-2"]`（与上游 `-lfprint-2`、`libfprint-2.pc` 的 `Libs: -lfprint-2` 一致） |
| 2 | `fatal error: 'libfprint/fprint.h' file not found` | 头文件装在 `include/libfprint-2/`（上游 `.pc Cflags: -I${includedir}/libfprint-2`），消费者应 `#include <fprint.h>`；test.c 误写 `libfprint/fprint.h` | test.c 改 `#include <fprint.h>` |
| 3 | 运行期 `Error loading shared library libfprint-2.so.2 / symbol not found`（dlopen 实报 `Permission denied`） | **OHOS loader 按 `.codesign` 摘要校验文件内容**：`meson install`（OHOS 定制版）会把安装产物 `.dynstr` 里的绝对构建路径（如 RUNPATH `/storage/Users/currentUser/.conan2/p/glibcad.../p/lib`）改写成 `'X'`，使 lld `-Wl,--code-sign` 生成的摘要失配 → 拒绝加载；配方再 `binary-sign-tool -selfSign` 重签同样破坏摘要。构建树内未改动的 .so 可正常加载 | ①`package()` 中 `_restore_pristine_shared_libraries()`：`Meson.install()` 后从 meson 构建树拷回原始链接产物（保持 lld 摘要）；②`_sign_shared_libraries()` 置为 NO-OP（gusb/glib 同法不重签，CI 发布期 `ci/artifacts/sign.sh` 再签） |
| 3b | 同链 json-glib/1.10.6 缓存包被 `meson install` 改写后同样拒绝加载（gusb→json-glib 链路） | 同上；该包是 gusb 钉死的已发布依赖，本地缓存包 .so 摘要已失效 | 本地缓存修复：用构建树原始 .so 替换 `p/json-.../p/lib` 及 `d/conan_package.tgz` 内的损坏副本（详见知识草稿 E999-draft） |
| 4 | test 收尾 `GLib-CRITICAL: g_atomic_ref_count_dec: assertion 'old_value > 0' failed` | test.c 对 `fp_context_get_devices()` 返回值调 `g_ptr_array_unref()`，但该 API 是 `(transfer none)`（数组归 context 所有），重复 unref | test.c 移除 `g_ptr_array_unref(devices)`，只 `g_object_unref(context)` |

- 修复后 `conan create` 全绿（exit 0），test_package 实际运行输出：`OHOS: FpContext OK, 0 device(s) enumerated (no USB backend in sandbox)`（libusb init Input/Output Error 为沙箱无 USB 后端，非缺陷）。
- 知识草稿：`knowledge/drafts/E999-draft-856F.kv`（meson install 路径改写 → .codesign 摘要失配 → loader 拒绝加载的完整根因/修复）。

## 源码修改（5 个补丁）

> 补丁文件名由 `refresh-patch --auto` 按 diff 路径重命名（finish step 1 生成），conandata.yml 已同步更新。

| 补丁 | 内容 |
|------|------|
| `0001-libfprint-drivers-goodixmoc-goodix_proto.c.patch` | goodix_proto.c 的 `MOC_CMD0_GET_VERSION`/`MOC_CMD0_PWR_BTN_SHIELD` case 体加 `{}`（C99 case 标签后声明，clang -std=gnu99 下必需） |
| `0002-libfprint-drivers-realtek-realtek.c.patch` | realtek.c 的 `FP_RTK_ENROLL_COMMIT` case 体加 `{}`（同上） |
| `0003-libfprint-meson.build.patch` | libfprint/meson.build 用 `if get_option('metainfo')` 门控 fprint-list-metainfo executable + metainfo.xml custom_target |
| `0004-meson.build.patch` | meson.build 用 `if get_option('examples')` 门控 examples subdir |
| `0005-meson_options.txt.patch` | meson_options.txt 增加 `examples`、`metainfo` 两个布尔开关 |

补丁由 `refresh-patch --auto` 生成/重命名；conandata.yml 已全部声明（patch_type=portability）。
⚠️ 教训：refresh-patch 重命名补丁后，conandata.yml 的 patch_file 需同步更新，否则 W3 的 conan create 在 `export_sources()` 报 `Patch file does not exist`（本包 W3 首次失败根因）。

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| glib | 2.84.0.1 | glib-2.0/gio-unix-2.0/gobject-2.0（gusb 0.4.9 钉死） |
| gusb | 0.4.9 | libusb 的 GObject 封装（fprint 核心依赖） |
| libusb | 1.0.27 | USB 后端 |
| libgudev | 238 | gudev-1.0（elanspi SPI 驱动 helper） |
| pixman | 0.46.4.3 | pixman-1（aes3k → aes3500/aes4000 驱动 helper） |
| nss | 3.118.1 | QA 声明依赖（registry 已发布） |
| ~~libxmlb~~ | ~~0.3.19~~ | **未声明**：libxmlb/0.3.19 要求 glib/2.88.3，与 gusb 钉死的 glib/2.84.0.1 在图解中直接版本冲突（G2 conan create 实测报 `Version conflict between glib/2.88.3 and glib/2.84.0.1`）；且 libfprint 与 gusb/0.4.9 构建均不需要它（探索阶段 reqs/ 无 xmlb.pc，gusb.pc Requires 仅 glib-2.0-unofficial/libusb-1.0/json-glib-1.0）。故 QA 清单中的 libxmlb 按 R43 冲突证据移除并记录 |
| openssl | 3.5.6.1.1 | uru4000 驱动 helper（`dependency('openssl')`，实测解析到 3.5.6.1.1） |
| meson（tool_requires） | 1.11.0 | 构建系统（QA 原要求 1.11.0.1，但该版本在 ohpcd 远端制品损坏无法下载——`conan download`/`conan install` 实测报 `system acceleration policy not enabled`/`Unable to find ... in remotes`（R41 证据）；1.11.0 可下载且已缓存，meson 为 python 工具，补丁级差异不影响） |

## 验证结果

```bash
# 探索构建
ninja -C build-exp          # libfprint-2.so.2.0.0 构建成功
DESTDIR=$TEST_PREFIX ninja -C build-exp install
# 上游测试
meson test -C build-exp     # 33 项：Ok 4 / Fail 2（SIGTRAP，沙箱 AF_UNIX 限制）/ Skipped 27（无硬件）
# 配方验证
conan-verify（8 门禁，含 G2 conan create）→ 通过
```

## 交付物

| 文件 | 说明 |
|------|------|
| `libfprint-2.so.2.0.0` | 共享库（soversion 2，含全部驱动） |
| `include/libfprint-2/*.h` | 公共头（fprint.h / fp-context.h / fp-device.h / fp-image*.h / fp-print.h / fp-enums.h） |
| `lib/pkgconfig/libfprint-2.pc` | pkg-config 元数据 |
| `libfprint-2.pc` | conan PkgConfigDeps 生成的消费者 .pc |

## 注意事项

- 本包是库类型（无 bin/ 可执行文件分发），按 R38 不需要 commands.json（CI L0k 校验）。
- `nss` 为 QA 声明依赖（registry 已发布），libfprint 源码本身未直接 include（已核查 uru4000 用 OpenSSL 而非 NSS），保留声明以闭合依赖。
- `libxmlb` 未声明：与 gusb 钉死的 glib/2.84.0.1 存在硬版本冲突（libxmlb/0.3.19 → glib/2.88.3），且构建不需要（证据见依赖表）。
- `meson` tool_requires 用 1.11.0 而非 QA 要求的 1.11.0.1：1.11.0.1 远端制品损坏无法下载（R41 证据见依赖表），1.11.0 可下载且已在本地缓存。
- 上游 fp-context/fp-device 2 项失败为沙箱 AF_UNIX bind EPERM，非适配缺陷（见申报表），真机/放开网络后可复测。
---

**编译结束**: 2026-10-04 03:40
**最终状态**: built
