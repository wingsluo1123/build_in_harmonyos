# wayland-utils 1.2.0 适配笔记

## 软件定位

**wayland-info**：连接 Wayland 合成器并打印其通告的协议 globals——接口名/
版本/请求计数、wl_shm 格式（fourcc）、输出/座位信息，启用 DRM 时额外打印
modifier 与 lease 信息。wayland 生态的标准诊断工具（weston-info 的继任者）。

- 上游：https://gitlab.freedesktop.org/wayland/wayland-utils
- 上游 tag：1.2.0（HTTP 200 实测）
- 构建系统：meson（>=0.47），单一 C 源（wayland-info/wayland-info.c，2424 行）
- 许可证：MIT/Expat

## 编译环境

- 构建系统: meson
- 上游版本: 1.2.0
- 编译日期: 2026-10-15
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 依赖（全部已在库）

| 依赖 | 版本 | 用途 | 备注 |
|---|---|---|---|
| wayland | 1.24.0 | wayland-client 头与 .so | 上游要求 >=1.20.0 ✅ |
| wayland-protocols | 1.48 | 5 组协议 XML（pkgdatadir） | 上游要求 >=1.24 ✅ |
| libdrm | 2.4.133 | DRM 信息打印（`-Ddrm=enabled`） | 上游要求 >=2.4.109 ✅ |

## 上游测试套件：0 项（清点实证）

tarball 完整文件清单（tar tzf 实测）：`meson.build`、`meson_options.txt`、
`wayland-info/{wayland-info.c,meson.build}`、`man/{meson.build,wayland-info.man}`、
`COPYING`、`README.md`、`.gitlab-ci.yml`——**无 tests/ 目录、无 test 目标、无
任何测试文件**。`.gitlab-ci.yml` 仅有编译矩阵（各类发行版容器里 meson build），
不含 meson test。

wayland-info **没有 --version 选项**（parse_cmdline 源码实证仅
`-h/--help` 与 `-i/--interface`）；`--help` 输出走 stderr 并 `EXIT_SUCCESS`。
无参调用时 `wl_display_connect` 失败 → "failed to create display" → 返回 -1
（255）。

因此本件列入 `ci/config/no_official_test.txt`（L1 白名单，yell/acpi_call 同款
先例：上游无自动化测试套件），功能验证由三层补测承担（见
test_package/MANIFEST.yml）。

## OHOS 适配四件事（全部有先例）

| # | 问题 | 根因 | 解决方案 | 先例 |
|---|------|------|----------|------|
| 1 | wayland/1.24.0 包内的 bin/wayland-scanner 无法 execve | OHOS 拒绝执行 conan 缓存内解出的二进制（实测 "operation not permitted"，exit 127） | 从 wayland 1.24.0 源码编译纯静态 scanner（-static 仅依赖 libc）到 generators 目录 + 合成 wayland-scanner.pc（meson 经 `dependency('wayland-scanner', native:true)` + `get_pkgconfig_variable('wayland_scanner')` 解析） | wayland-protocols/1.36.1、1.48；wayneko |
| 2 | 依赖 .pc 的 prefix 解析不出真实路径 | wayland/libdrm 发布包 .pc 写 `prefix=/`；wayland-protocols 写 `pkgdatadir=${pc_sysrootdir}${datarootdir}/...` | 消费侧在 `<generators>/fixed_pkgconfig/` 改写副本（prefix 重写 + pkgdatadir 绝对化）置顶 PKG_CONFIG_PATH——**纯消费侧首个实例**（库/数据包是在自己 package() 时修 .pc，消费者改不了发布包只能影子化） | wayland/1.24.0（自家修）；本件（消费侧修） |
| 3 | meson 找不到 llvm-ar | HMDFS 软链接在 meson subprocess 中解析失败 | native file 注入 `ar` 路径 + native [paths] pkg_config_path | zix/serd/wayland/wayland-protocols |
| 4 | CI L2 冒烟裸跑 bin/wayland-info（无 conanrun env），OHOS 无 ld.so.conf 指向 conan 缓存 | 动态链接 libwayland-client.so.0 的二进制裸跑会找不到库 | patchelf 嵌入 DT_RUNPATH 指向 wayland 包 libdir（实测 RUNPATH→缓存 .so 的 aarch64 ELF 裸跑成功）+ OHOS 自签（binary-sign-tool） | wmcdplay（drop rpath 的逆向用法）；wayneko（签名） |

## 关键技术核验（真机实证，2026-10-15）

- 静态二进制（clang -static）新建即可执行 ✅
- RUNPATH 指向 conan 缓存 lib 的动态二进制裸跑成功（wl_display_connect 真实
  被调用，无合成器时优雅报错退出）✅
- conan 缓存目录内二进制 execve → "operation not permitted" (127) ✅（证
  实静态 scanner 方案必要性）
- meson 1.12 保留 `dependency.get_pkgconfig_variable`（FeatureDeprecated
  0.56 仍可用，warning 而非 error；wayland-protocols 1.48 真机构建已验证同款
  用法）✅
- meson `configure_file` 根目录产出 config.h：上游 wayland-info/meson.build
  经 `dir_inc = include_directories('.')`（根 meson.build）解析 `#include
  "config.h"` ✅（实验验证：子目录 include_directories('.') 指向源码根，根
  config.h 可见；无需 patch）

## 源码修改

**无补丁**（`patches: {}`）。所有适配都在 conanfile.py 的 generate()/
package() 内处理（.pc 影子化 + native file 注入 + RUNPATH 嵌入 + 自签）。

## 生成协议

wayland-info/meson.build 对 wayland-protocols 1.48 的 5 组协议各生成
client-header + private-code（scanner >=1.14.91 走 private-code 模式）：

| 协议 | 状态 | 接口（版本） |
|---|---|---|
| presentation-time | stable | wp_presentation (2) |
| drm-lease-v1 | staging | wp_drm_lease_device_v1 (1) 等 4 接口 |
| linux-dmabuf-unstable-v1 | unstable | zwp_linux_dmabuf_v1 (5) 等 3 接口 |
| tablet-unstable-v2 | unstable | zwp_tablet_manager_v2 (1) 等 5 接口 |
| xdg-output-unstable-v1 | unstable | zxdg_output_manager_v1 (3) 等 2 接口 |

## 三层测试体系（上游 0 测试，全部为鸿蒙侧补测）

1. **层 1（消费者 E2E 源级）**：test_package/src/test_wayland_info_e2e.c —— 由
   test_package 复用主配方源码树内编译的静态 scanner 对 5 组协议 XML 重新生
   成绑定产物（与上游 wayland-info/meson.build 的 generated_protocols 字典一
   致，19 个接口），编译链接后逐接口核对 `wl_*_interface` 数据符号（接口名/
   版本/请求计数）与包内 XML 原文 —— **19 用例 × 4 检查点 = 76 项**，末行
   TEST SUMMARY，任一失败退出码 1；
2. **层 2（消费者 CLI）**：test_package/test.sh —— 执行安装出的 bin/
   wayland-info（经 conanrun PATH + RUNPATH），断言 --help/-h 退出码 0 与
   usage 文案、未知选项退出码 1 与 "Unknown option"、-i 缺参退出码 1 与
   "Missing interface name"、无参运行优雅失败（"failed to create display"，
   无合成器环境）、readelf 级 ELF 属性（AArch64/PIE/NX/RELRO/DT_NEEDED）、
   RUNPATH 指向、env -i 裸跑冒烟 —— **20 断言**；
3. **层 3（鸿蒙特有）**：test_package/test_wayland_info_ohos.c —— 仅 OHOS
   编译（`#ifndef __OHOS__ #error` 守卫），对安装出的二进制做 ELF 级断言：
   ELF64/AArch64/PIE/INTERP/NX/RELRO/DT_NEEDED（libwayland-client.so.0 +
   libc.so）/DT_RUNPATH（指向 wayland 包 libdir）共 12 项平台属性 + 19 项
   协议接口数据符号存在性（.symtab 内 STT_OBJECT 且已定义）—— **31 断言**。

合计 **127 断言**（76+20+31）。三层全部由 test_package 的 test() 驱动，
test_package/conanfile.py 内 self.run() 留下 CI L1a 可识别的执行痕迹。

## 已知限制

- 无合成器环境（CI/沙箱）下无法做端到端的"连接真实 compositor"测试——层 1
  的接口数据核对 + 层 2 的 CLI 契约 + 层 3 的 ELF 断言已覆盖可静态验证的全
  部面。
- 层 1/层 3 测试二进制在沙箱内自签（binary-sign-tool 缺失时裸跑，实测可
  执行）。

## 本轮构建修复（2026-10-16，通道重派续跑；conan create 真机全绿）

本轮把 `conan create . --build=missing -pr:h=ohos-aarch64-local
-pr:b=ohos-aarch64-local` 从"三个 package/test 阶段硬失败"推进到全绿
（层 1 = 76、层 2 = 20、层 3 = 31，合计 127 断言全过）。共 4 处修复：

### 修复 1：SDK 宿主工具（patchelf / llvm-objcopy / binary-sign-tool）的
### LD_LIBRARY_PATH（根因：worker 的 LD_LIBRARY_PATH 被"污染"）

- **现象**：`package()` 调 patchelf 报 `CalledProcessError ... exit status
  127`；改用/修好后 binary-sign-tool 又报 `exit 127`，stderr 全是
  `Error loading shared library libc++_shared.so` /
  `_ZNSt4__n1... symbol not found`（patchelf 需 `std::__n1` 的 libc++）与
  `_ZNSt3__h... symbol not found`（binary-sign-tool 需 `std::__h` 的
  系统 `libc++.so`）。
- **根因**：这三个 SDK 工具本身是**动态链接**的 OHOS 二进制。`subprocess.run`
  继承调用方的 `LD_LIBRARY_PATH`，而 worker 上该变量带一个**畸形条目**
  `"         /system/lib64"`（9 个前导空格）——加载器把它当成无效路径，
  于是干净的 `/system/lib64` 从未被搜索；同时 `libc++_shared.so`（`__n1`）
  实际位于 `$SDK/llvm/lib/aarch64-linux-ohos` 与 `/system/lib64`，
  而**不**在 `$SDK/llvm/lib`（CI profile `[buildenv]` 只列了后者）。
- **修复**：配方新增 `_sdk_lib_dirs()` + `_tool_env()`，从 clang 真实路径
  反推 SDK 根，构造显式 `LD_LIBRARY_PATH`，顺序为
  **`/system/lib64` 最前**、再 `$SDK/llvm/lib/aarch64-linux-ohos`、
  `$SDK/llvm/lib`、最后追加原值。`/system/lib64` 必须最前：binary-sign-tool
  需要系统 `libc++.so`（`__h`），而 `$SDK/.../aarch64-linux-ohos/libc++.so`
  只是链接脚本 `INPUT(-lc++_shared)`，若 SDK 目录先被搜索，加载器会上到
  这个非 ELF 文件 → 86 个 `__h` 符号 not found。`/system/lib64` 同时含
  `libc++_shared.so`（`__n1`），故对 patchelf 亦成立。patchelf /
  llvm-objcopy / binary-sign-tool 三处 `subprocess.run` 均改用该 env。

### 修复 2：test_package 的 `_pkgdatadir()` 不再信任 wayland-protocols 包内
### `.pc` 的 prefix（根因：发布包 .pc 内嵌陈旧构建暂存路径）

- **现象**：test_package `build()` 报
  `ConanException: pkgdatadir invalid:
  '/storage/Users/currentUser/.cache/conan2/p/b/wayla3c1508aeaa1b7/p/share/wayland-protocols'`。
- **根因**：缓存中的 `wayland-protocols/1.48` 包内 `.pc` 写着
  `prefix=/storage/Users/currentUser/.cache/conan2/p/b/wayla3c1508aeaa1b7/p`
  ——一个**构建期暂存目录**（且属于另一个 conan home `.cache/conan2`），
  当前 worker 上不存在；`datarootdir=${prefix}/share` 于是把 pkgdatadir
  解析成不存在的路径。`wayland-protocols.pc` 因此**不可 relocate**。
- **修复**：`_pkgdatadir()` 改为**以包布局为准**，直接返回
  `<wayland-protocols 包目录>/share/wayland-protocols`（主配方 `generate()`
  早已用 `wp_base` 重写 .pc 的 prefix+pkgdatadir，故主构建不受影响），仅在
  布局异常时才回退解析 `.pc`。

### 修复 3：层 1 E2E 测试需显式链接 libwayland-client

- **现象**：`ld.lld: error: undefined symbol: wl_surface_interface`（还有
  wl_output_interface / wl_buffer_interface / wl_seat_interface）。
- **根因**：wayland-scanner 生成的协议 `private-code` 会引用核心
  `wl_*_interface` 对象（定义在 libwayland-client）。
- **修复**：层 1 编译命令追加 `-L<wayland 包 libdir> -lwayland-client`。

### 修复 4：层 1 "请求计数 > 0" 断言对纯事件接口误报

- **现象**：层 1 运行 `75 passed, 1 failed`，失败项为
  `stable/presentation-time.wp_presentation_feedback` 的"请求计数"。
- **根因**：`wp_presentation_feedback` 是**纯事件接口**（0 个 request，
  2 个 event），`method_count > 0` 的假设不成立。
- **修复**：断言改为 `method_count + event_count > 0`（"接口已被填充"），
  标签改为"方法/事件计数"；层 1 恢复 76/76。

> 说明：修复 1/2 属于**跨库可复用的平台差异诊断**（SDK 宿主工具运行时
> 解析 + 发布包 .pc 不可 relocate），是路径 B 知识草稿的候选素材。
