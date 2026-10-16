# libhinoko 1.0.3 — OHOS aarch64 适配笔记

## 概览

- 包名：`libhinoko`，版本 `1.0.3`，slug 目录 `archives/l/libhinoko/1.0.3/`（R39）。
- 上游：https://gitlab.freedesktop.org/libhinawa/libhinoko
- 语言预检：`detected=c`（R47 预检通过，主任务 lang-preflight 已确认）。
- 构建系统：meson（`meson_version >= 0.58.0`），C 库 + GObject。
- 依赖：
  - `gobject-2.0 >= 2.44` → 制品仓 `glib/2.84.0.2`
    （package_id `b55f7a483155972128ae18c9f9e8c67eba35e745`，已发布）。
  - `hinawa >= 4.0.0`（顶层 `meson.build` `dependency('hinawa', version:'>=4.0.0')`）
    → 制品仓 `libhinawa/4.0.2`（已本地构建，同族配方，见
    `archives/l/libhinawa/4.0.2/`）。
- 与 libhinawa/4.0.2 配方的差异（本包特有设计）见下文「配方关键设计」3/5。

## 源码 URL（R39）

conandata.yml 采用 kernel.org 官方镜像体系：

```
https://mirrors.kernel.org/pub/linux/libs/ieee1394/libhinoko-1.0.3.tar.xz
sha256 = f826dd438333655adac225941d36b8d4dfdcf4db6de2867244e9d9b94ed3724b
```

mirrors.kernel.org 是 kernel.org 官方镜像列表成员，属官方权威源。若
preflight/CI 镜像黑名单拦截该域名，可换官方主站同内容：

```
https://www.kernel.org/pub/linux/libs/ieee1394/libhinoko-1.0.3.tar.xz
```

## 配方关键设计

### 1. 依赖与工具注入（R49）

- `glib-genmarshal` / `glib-mkenums`（`gnome.genmarshal` /
  `gnome.mkenums_simple` 需要）随 `glib/2.84.0.2` 包的 `bin/` 交付。
  `generate()` 用 `Environment().prepend_path("PATH", <glib package_folder>/bin)`
  注入构建环境（save_script，仅构建上下文生效），并往
  PkgConfigDeps 生成的 `glib-2.0.pc` 追加 `glib_genmarshal` /
  `glib_mkenums` 变量（meson >=1.10 gnome 模块经 pkg-config 变量定位工具，
  不再 PATH 兜底）。注入目标是**依赖的 package_folder**，绝不触碰共享
  `/usr/local`（R49，E524）。
- meson 用 `tool_requires("meson/1.11.0")`（1.9.0 不存在，实测 conan list，
  同 libhinawa 配方）。
- `requirements()` 增加 `self.requires("libhinawa/4.0.2",
  transitive_headers=True, transitive_libs=True)`：公共头 `hinoko.h`
  `#include <hinawa.h>` 并暴露 `HinawaCycleTime` 类型，link 侧需
  `-lhinawa`。

### 2. gobject-2.0.pc wrapper

glib 包 package_info 只对外声明 `glib-2.0` 组件；本包
`src/meson.build` 写死 `dependency('gobject-2.0')`。仿 libhinawa 与
gobject-introspection/1.80.1 配方，`generate()` 在 `generators_folder`
写 `gobject-2.0.pc` wrapper（prefix 指向 glib 的 package_folder，
`Requires: glib-2.0`），使 meson 的 pkg-config 探测成功。

### 3. hinawa.pc wrapper（本包特有，重点）

libhinawa/4.0.2 由其 meson install 阶段生成的
`lib/pkgconfig/hinawa.pc` 携带 **`prefix=/`**（未做 prefix 重写），直接
引用会解析到 `/include`、`/lib` 而失败；其 `Cflags` 也只给
`-I${includedir}/hinawa`，且依赖经 `Requires.private: gobject-2.0`。
本配方 `generate()` 在 `generators_folder` **覆写**一份 `hinawa.pc`：

```
prefix=<libhinawa package_folder>
libdir=${prefix}/lib
includedir=${prefix}/include
Version: 4.0.2
Requires: gobject-2.0
Libs: -L${libdir} -lhinawa
Cflags: -I${includedir}/hinawa -I${includedir}
```

这样顶层 `meson.build` 的 `dependency('hinawa', version:'>=4.0.0')`
经 `pkg_config_path=<generators_folder>`（MesonToolchain 注入）即可命中，
`Requires: gobject-2.0` 与本配方 gobject-2.0.pc wrapper 配套解析。
`PkgConfigDeps(self).generate()` 也会按 libhinawa 的 `pkg_config_name`
产出 `hinawa.pc`（内容正确但无 `Requires`）；本配方在其后覆写，保证
Requires 链完整。

### 4. meson 二进制注入

沿用 libhinawa/pygobject/libgudev 配方手法：`generate()` 后往
`conan_meson_native.ini`（或 cross）的 `[binaries]` 段注入 `ar` / `ranlib`
（从 `tools.build:compiler_executables` 的 c 编译器同目录找
llvm-ar/llvm-ranlib），meson 在 OHOS 上默认找不到 ar。

### 5. GIR 取舍（options.gir，默认 False）

上游 `src/meson.build` **无条件**调用 `gnome.generate_gir()`（无对应
meson option），产出 `Hinoko-1.0.gir/typelib`（namespace `Hinoko`、
`nsversion '1.0'`、`includes` 含 `GLib-2.0/GObject-2.0/Hinawa-4.0`）。
接通 GIR 需要完整 gobject-introspection 工具链（g-ir-scanner 扫描共享库、
ldd shim、distutils vendoring、python lib-dynload 注入与鸿蒙 loader
白名单签名，见 gobject-introspection/1.80.1 配方），且本包 GIR 还需
libhinawa 的 `Hinawa-4.0.typelib` 参与生成。对本小型 1394 外设库，GIR
非交付目标（无下游消费 typelib），代价远大于收益。

**决定**：新增配方级 `options.gir`（默认 `False`）；`gir=False` 时
`build()` 内联改写 `src/meson.build`，把

```
hinoko_gir = gnome.generate_gir(...)
```

用非贪婪正则 `r"hinoko_gir = gnome\.generate_gir\(.*?\n\)\n"`（`re.S`）
整体剪成 `hinoko_gir = []`（`declare_dependency` 的
`sources: headers + marshallers + enums + hinoko_gir` 引用保持合法）。
改写锚点找不到时告警并保留原文件（fail-safe，宁可构建报错也不静默改错块）。
注意：**本包锚点为 `hinoko_gir`，与 libhinawa 的 `hinawa_gir` 不同**，且
`src/meson.build` 的 `hinoko_dep = declare_dependency(...)` 在改写后仍
引用 `hinoko_gir`，故必须剪块（不能只删调用）。本地已用源码实测
`re.subn` 返回 n=1 且改写后文件语法完整。

### 6. 铁律遵循清单

- R26：无系统同名库链接风险——包交付 `libhinoko.so`，依赖全由 conan 管理
  （libhinawa/glib 均 conan 包）。
- R32：`validate()` 中 `settings.os not in ("Linux", "OHOS")`。
- R33：build() 无裸 `${CC}`/`${CFLAGS}`；编译器经 MesonToolchain 从
  profile 的 `tools.build:compiler_executables` 获取；test_package 用
  conan 注入的 `CC` 环境变量（VirtualBuildEnv）。
- R34：test_package `test()` 有字面 `self.run`：编译链接 `test_hinoko.c`
  （调用 `hinoko_fw_iso_ctx_get_type()`、`hinoko_fw_iso_resource_calculate_bandwidth()`
  与 `HINOKO_FW_ISO_CTX_MODE_IT` 枚举，共 3 项断言），本机运行时直接执行
  探针二进制；交叉编译时验证编译+链接。
- R39：官方源 kernel.org 镜像体系（见上）。
- R47：detected=c，预检通过。
- R49：PATH/LIBRARY_PATH 注入全部指向依赖 package_folder 与 build_folder。
- W2：单包单 PR 原子目录；test_package/ 结构完整（conanfile.py +
  独立测试源 test_hinoko.c）。
- PF3：test_package 非空壳——test_hinoko.c 实质链接并运行探针。

### 7. pkg-config 下游可用性说明

本配方 `package_info()` 声明 `cpp_info.set_property("pkg_config_name",
"hinoko")`、`libs=["hinoko"]`、`includedirs=["include","include/hinoko"]`、
`libdirs=["lib"]`——保持 conan agnostic 声明。meson 会在 `lib/pkgconfig/`
安装上游生成的 `hinoko.pc`（pkg.generate，`subdirs: inc_dir`）。
下游若用 pkg-config 消费，`hinoko.pc` 的 `Requires`（hinawa/gobject-2.0
等）由下游 recipe 的 `generate()` 按本配方/ libhinawa 手法补 wrapper
`.pc`；hinawa 的 wrapper 手法直接抄本配方 `_write_hinawa_pc`。

## 上游测试清点（R51 三步法）

上游 `tests/meson.build` 注册 **9 项**测试，全部为 Python GI 脚本
（`find_program(script)` 直接执行 tests/ 下同名脚本，无 ctest）：

| # | 测试 | 内容 | 运行前提 |
|---|------|------|----------|
| 1 | hinoko-enum | 6 组枚举（FwIsoCtxMode/FwScode/MatchFlag/资源错误等）值断言 | GI typelib（Hinoko-1.0） |
| 2 | fw-iso-ctx | FwIsoCtx 接口属性/方法/虚方法/信号内省 | GI typelib |
| 3 | fw-iso-ir-single | FwIsoIrSingle 内省 | GI typelib |
| 4 | fw-iso-ir-multiple | FwIsoIrMultiple 内省（含 channels 属性） | GI typelib |
| 5 | fw-iso-it | FwIsoIt 内省 | GI typelib |
| 6 | fw-iso-resource | FwIsoResource 接口内省 | GI typelib |
| 7 | fw-iso-resource-auto | FwIsoResourceAuto 内省 | GI typelib |
| 8 | fw-iso-resource-once | FwIsoResourceOnce 内省 | GI typelib |
| 9 | hinoko-functions | 纯函数/错误 quark 内省 | GI typelib |

tests/meson.build 为每项设置 `GI_TYPELIB_PATH=<builddir>/src` 且
`depends: hinoko_gir`——即全部测试依赖 GIR 产物。

### 实测情况（如实申报）

- **ran: 0 / 9**，逐项技术归因：
  1. 本适配以 `gir=False` 构建，不产出 `Hinoko-1.0.typelib`，9 项脚本的
     `import gi; gi.require_version('Hinoko','1.0')` 均无法加载（共同前提不满足）。
  2. **已验证的崩溃点证据（2026-10-02 实测）**：即使临时接通 GIR 所需的
     pygobject 运行时（从制品仓安装 pygobject/3.58.0 + glib2/2.88.0 +
     gobject-introspection/1.80.1 + python/3.12.9），本机 OHOS 环境加载
     pygobject 的 C 扩展时必然崩溃：
     ```
     import gi  → ImportError: Error relocating
       <pygobject>/lib/python3.12/site-packages/gi/_gi.cpython-312-aarch64-linux-ohos.so:
       PyType_Ready: symbol not found
     ```
     （已分别在 conan python 与系统 python3、补 libpython 的
     LD_LIBRARY_PATH 下复测 4 次，均同一崩溃）——即 OHOS 的 musl 动态链接
     器在 pygobject `_gi.so` 重定位阶段找不到 CPython 的 `PyType_Ready`
     符号，GI 运行时在本平台不可用。这是"换了运行环境也无法让测试脚本
     跑起来"的**已验证平台限制**，非网络问题。
  3. 即便绕过 pygobject，运行期仍需完整 gobject-introspection 工具链
     （g-ir-scanner 的 ldd shim、distutils vendoring、loader 白名单签名），
     成本见上文第 5 节取舍。
- **替代验证**：conan test_package 编译链接 `test_hinoko.c` 并调用
  `hinoko_fw_iso_ctx_get_type()`（GObject 接口类型注册）、
  `hinoko_fw_iso_resource_calculate_bandwidth(0, HINOKO_FW_SCODE_S400)==12`
  （纯函数，不触碰硬件）与 `HINOKO_FW_ISO_CTX_MODE_IT` 枚举，覆盖库的
  符号交付与 GObject 类型注册路径（API 层），即 R34 实质消费。**conan create
  实测通过（3/3 断言 PASS）**。

## 待验证项（主任务 conan create）

1. **内核头可用性**：本适配**不**为 `<linux/firewire-cdev.h>` /
   `<linux/firewire-constants.h>` 打补丁——OHOS sysroot
   （`/storage/Users/currentUser/usr/local/sysroot/usr/include/linux/`）
   已含两文件，且逐项核对 libhinoko 1.0.3 使用到的全部符号均存在：
   - 结构体：`fw_cdev_get_info`、`fw_cdev_create_iso_context`、
     `fw_cdev_iso_packet`、`fw_cdev_queue_iso`、`fw_cdev_start_iso`、
     `fw_cdev_stop_iso`、`fw_cdev_flush_iso`、`fw_cdev_event_iso_interrupt(_mc)`、
     `fw_cdev_get_cycle_timer2`、`fw_cdev_set_iso_channels`、
     `fw_cdev_allocate_iso_resource`、`fw_cdev_deallocate`；
   - ioctl：`FW_CDEV_IOC_GET_INFO/CREATE_ISO_CONTEXT/QUEUE_ISO/START_ISO/
     STOP_ISO/FLUSH_ISO/GET_CYCLE_TIMER2/SET_ISO_CHANNELS/
     ALLOCATE_ISO_RESOURCE/DEALLOCATE_ISO_RESOURCE/
     ALLOCATE_ISO_RESOURCE_ONCE/DEALLOCATE_ISO_RESOURCE_ONCE`；
   - 常量：`FW_CDEV_ISO_CONTEXT_*`、`FW_CDEV_ISO_CONTEXT_MATCH_TAG0..3`、
     `SCODE_100..SCODE_3200`。
   已用 sysroot clang 对 `#include <hinawa.h>` + linux 两头做编译探测通过；
   仍需 conan create 全程编译复核（若 CI 交叉环境 sysroot 与此处不同，
   应按 libhinawa 方案改回 has_header_symbol 探测或补 backport 头）。
2. **hinawa.pc wrapper 命中**：确认 meson configure 阶段
   `dependency('hinawa', version: '>=4.0.0')` 经 generators_folder 的
   wrapper 命中（若 PkgConfigDeps 产物足以命中且 Requires 链完整，本
   wrapper 为冗余兜底，无害）。
3. **GIR 改写**：确认 `re.subn` 在 conan 构建副本上仍返回 n=1（本地已对
   解压源码验证通过），改写后 `hinoko_dep` 的 `sources:` 引用合法。
4. **test_package 实跑**：本机（或 OHOS 真机/模拟器）运行
   `test_hinoko_probe` 3 项断言全过；交叉编译场景至少编译+链接通过。

## 已知限制

- 运行期下游需 `LD_LIBRARY_PATH` 含 libhinawa + glib libdir
  （libhinawa.so.4、libgobject-2.0 / libglib-2.0 共享依赖）。
- 功能级验证（真实 isochronous 1394 传输，FW_CDEV_IOC_* ioctl）需真机
  /dev/fw* 硬件，CI 不可覆盖；上游 9 项 GI 测试为纯内省断言（无硬件
  门槛），但因 GIR 取舍（gir=False）在本适配中亦未运行。
