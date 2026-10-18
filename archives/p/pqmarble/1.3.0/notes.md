# pqmarble 1.3.0 适配笔记

- 适配日期: 2026-10-17
- 上游: <https://gitlab.gnome.org/raggesilver/marble> tag `v1.3.0`（commit `710a677afa9fab25f2a9ef2161cc80dff23b747d`）
- 构建系统: Meson 1.11.0 + Ninja 1.12.1 + Vala 0.56.19（valac 转 C，产出 C ABI 共享库）
- 目标平台: OHOS 6.0 / armv8 / clang 15（profile `ci/conan/profiles/ohos-aarch64`）

## 0. 身份与版本映射（W0b）

任务书 `pqmarble/1.3.0` 的 Debian 源码包 `pqmarble 1.3.0-7` 实际内容是上游 master
快照（内部 project version 2.0.0、GTK4）；与本版本号语义一致的是上游 tag `v1.3.0`
（`project('marble', version: '1.3.0')`，GTK3）。本适配取**官方 tag**，避免使用
Debian 重打包源码（R39）。

## 1. 依赖（R36 已核实可消费）

直接依赖（版本按 `gtk/3.24.43` 配方的实际 pin 选定，避免依赖图冲突）：

| 依赖 | 用途 | 来源 |
|------|------|------|
| `glib/2.84.0.1` | gio-2.0 / gobject-2.0 | ohpcd 制品仓 |
| `gtk/3.24.43` | gtk+-3.0（OHOS 侧 broadway 后端） | ohpcd 制品仓 |

构建工具：`meson/1.11.0`、`ninja/1.12.1`、`vala/0.56.19`、`pkgconf/3.0.6`。
依赖闭包 28 个第三方包在适配前已用 `conan download <pkg>/<ver> -r=ohpcd --only-recipe`
逐条实测 exit 0（证据：`../pqmarble-1.3.0-deps/logs/exit-codes-*.log`）。

## 2. 上游测试入口清点（R51 第 1 步）

| 文件 | 作用 |
|------|------|
| `src/tests/meson.build` | `-Dtests=true` 时构建 `marble_test` |
| `src/tests/test.vala` | `Gtk.Application` 交互式演示窗口（无断言） |
| `src/tests/marbletest.gresource.xml` / `layouts/marbletest.ui` | 测试窗口 UI 资源 |
| `test.sh` / `Makefile` | flatpak-builder 驱动的 `make test` / `make test-run` |

结论：上游**没有自动化测试**（无 `test()` 注册、无断言框架），`meson test` 输出
`No tests defined.`；唯一的“测试”是 GUI 交互程序 `marble_test`。

## 3. 适配过程中遇到的真实错误与修复

日志目录: 仓库外任务工作区 `pqmarble-1.3.0-logs/`（`create-*.log`、`testpkg-*.log`、
`upstream-*.log`、`conan-verify-01.log`、`finish-*.log`）

### 3.1 `source()` TypeError

- 首个错误：`TypeError: get() got an unexpected keyword argument '1.3.0'`
- 根因：`self.conan_data["sources"]` 还差一层版本 key。
- 修复：`get(self, **self.conan_data["sources"][self.version], strip_root=True)`。

### 3.2 meson `Unknown linker(s): [['llvm-ar']]`

- 日志：`create-04.log`
- 根因：OHOS worker 的 PATH 只有 `clang`/`clang++`，没有 `llvm-ar`；meson 在
  `project()` 阶段探测 clang 配套静态链接器失败。
- 修复：从 profile `tools.build:compiler_executables.c` 的目录推导
  `llvm-ar/llvm-ranlib/llvm-strip`，写入 machine file `[binaries]`。

### 3.3 `Could not execute Vala compiler: valac`

- 日志：`create-05.log`；meson-log 里是 `Detecting compiler via: valac --version -> [Errno 2]`
- 根因 1：meson 的 vala 探测按程序名查 PATH，OHOS 上不可靠。
- 根因 2：即使找到 valac，vapi 搜索目录是 valac 编译期硬编码前缀，conan 包重定位后
  `<pkg>/share/vala-0.56/vapi` 不在搜索路径内 → `Package 'posix' not found in
  specified Vala API directories`。
- 修复：生成 `<generators>/build-tools/valac` wrapper（`exec valac --vapidir=<vapi 目录> "$@"`），
  并把 wrapper 绝对路径写进 `[binaries] vala`；同时把 generators 目录补进
  `PKG_CONFIG_PATH`（valac 内部要自调 pkg-config 解析 `--pkg`）。

### 3.4 `Could not get pkg-config variable ... for gio-2.0`

- 日志：`create-05`/`create-07` 之间的手工复现（`src/meson.build:14`）
- 根因：`gnome.compile_resources()` 走 `state.find_tool()`：先查 machine file
  `[binaries]`，查不到才读 `gio-2.0.pc` 的 `glib_compile_resources` 变量；PkgConfigDeps
  生成的 .pc 没有该变量。
- 修复：把 glib 包 `bin/` 的 `glib-compile-resources` 等显式写进 `[binaries]`。

### 3.5 `glib-compile-resources: Operation not permitted`（EPERM）

- 日志：`create-07.log`
- 根因：conan 包内的 ELF 构建工具**没有签名**，OHOS 拒绝 execve（EPERM）。
- 修复：复制到 `<generators>/build-tools/`，`chmod 755` 后用
  `/data/service/hnp/bin/binary-sign-tool sign -selfSign 1` 自签名；`#!` 脚本类工具
  （`glib-mkenums`/`glib-genmarshal`/`gdbus-codegen`）改写成显式 python3 wrapper。

### 3.6 `Could not find GIR file 'GObject-2.0.gir'`

- 日志：`create-08.log`
- 根因：`src/meson.build` 用 `g-ir-compiler` 把 `Marble-1.3.0.gir` 编译成 typelib，
  但 GIR 里 `<include name="GObject" version="2.0"/>` 需要 GLib/GObject 的 GIR；
  OHOS 侧 `glib/2.84.0.1`、`gtk/3.24.43` 包**未安装任何 .gir**（构建时 introspection 关闭），
  `g-ir-scanner` 也不可用（gobject-introspection 包缺 `_giscanner` C 扩展、Python 3.12
  无 distutils）。`.gir` 本身由 valac 直接生成，不依赖 scanner。
- 修复：`patches/0001-meson-optional-typelib.patch` 增加 meson option
  `introspection_typelib`（默认 true），把 typelib custom_target 包进去；配方
  `-Dintrospection_typelib=false`（`with_typelib` 选项默认 False）。
  交付物仍包含 `marble.h`、`marble.vapi`、`Marble-1.3.0.gir`、`marble.pc`。

### 3.7 test_package 运行期 `Error loading shared library libmarble.so.1`

- 日志：`create-10.log` / `testpkg-01.log`
- 根因：OHOS 加载器拒绝加载未签名 ELF 共享库（包内 `libmarble.so.1.3.0` 是刚构建的）。
- 修复：`package()` 末尾 `_sign_installed_elfs()`，对 `lib/**/*.so*`（跳过符号链接）
  逐个 `binary-sign-tool -selfSign`。
- 复验：`conan test test_package pqmarble/1.3.0 ...` 全部 PASS（见 `reports/test-report.md`）。

## 4. 构建产物

```
lib/libmarble.so.1.3.0        (SONAME libmarble.so.1，已签名)
include/marble.h
share/vala/vapi/marble.vapi
share/vala/vapi/marble.deps
share/gir-1.0/Marble-1.3.0.gir
lib/pkgconfig/marble.pc
```

`bin/marble_test`（上游 `-Dtests=true` 产生的交互式测试程序）在 `package()` 中被剔除，
不进入交付包。

## 5. 待办

（无）
---

**编译结束**: 2026-10-17 21:11
**最终状态**: built
