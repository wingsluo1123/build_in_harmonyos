# gtkmm 3.24.11 适配笔记

## 编译环境
- 构建系统: meson（官方 release tarball，`meson dist` 产物自带 untracked/ 预生成绑定）
- 编译日期: 2026-10-15
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 平台: HarmonyOS PC (OHOS aarch64；GTK+3 为 Broadway-only 图形配置)
- 状态: built

## 任务背景
gtkmm 3.24.11 = **gtkmm-3.0 ABI 线**（pkg-config `gtkmm-3.0` / `gdkmm-3.0`），
与仓库已有 gtkmm 4.0.0/4.0.0.1（gtkmm-4.0 ABI 线）并存，二者 ABI 与依赖链
完全不同：

| ABI 线 | gtkmm | glibmm | cairomm | pangomm | atkmm | sigc++ |
|---|---|---|---|---|---|---|
| gtkmm-3.0（本版本） | 3.24.11 | glibmm-2.4（2.66.9） | cairomm-1.0（1.14.5.1） | pangomm-1.4（2.46.5） | atkmm-1.6（2.28.4） | sigc++-2.0 |
| gtkmm-4.0（已有） | 4.0.0.x | glibmm-2.68（2.68.2） | cairomm-1.16（1.18.0） | pangomm-2.48（2.50.1） | 无（GTK4 移除 atkmm） | sigc++-3.0 |

上游版本选择：GNOME 官方 3.24 分支最新 = 3.24.11（2026-06-09）。

## 编译步骤

1. **W0 依赖发布检查**（`conan download --only-recipe -r=ohpcd`）：
   glibmm/2.66.9、atkmm/2.28.4、cairomm/1.14.5.1、pangomm/2.46.5、
   gtk/3.24.43、gdk-pixbuf/2.44.6.1、libsigc/2.12.1 均已发布。
2. **源码**：`https://download.gnome.org/sources/gtkmm/3.24/gtkmm-3.24.11.tar.xz`
   （sha256 `19e383c82d5dd89db275e00b82864e90414d4c3fb3d100b2f996bcc2338a4cc7`，
   与官方 `.sha256sum` 一致）。
3. **Conan 配方**：meson + PkgConfigDeps + MesonToolchain：

   ```bash
   conan create archives/g/gtkmm/3.24.11 \
     -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
     --build=missing
   ```

   meson 选项：`default_library=shared`、`maintainer-mode=false`、
   `build-documentation=false`、`build-demos=false`、`build-x11-api=false`、
   `build-tests=true`、`wrap_mode=nodownload`。
4. **上游测试**：`meson test -v -C <build> --timeout-multiplier=16 --no-rebuild --no-suite=failing`
   → `gdk_rgba_test` OK（1/1，Fail 0）。
5. **test_package 消费者测试**：clang++ 直接编译 `test.cpp` 链接
   `-lgtkmm-3.0 -lgdkmm-3.0 ...`，原生运行 → `gtkmm-3.0 probe: checks=11 PASS`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 判定 `build_system=autotools`，meson 模板未生成 | gtkmm 3.24 官方 tarball 只带 `configure.ac`（无 `configure`）——上游已迁移到 meson；init-build 按 URL/文件名关键词误判 | 手写 meson 配方，manifest `build.system=meson` 覆盖 |
| 2 | 图中 `libsigc/2.10.8` 与 `2.12.1` 版本冲突（ERROR Version conflict） | glibmm/2.66.9 钉 libsigc/2.10.8；cairomm/1.14.5.1 与 pangomm/2.46.5 钉 libsigc/2.12.1 | 配方 `self.requires("libsigc/2.10.8", override=True)`（对齐 glibmm 的 pin；sigc++-2.0 在 2.x 内 ABI 稳定）。**裁决依据**：`override` 会让包 id 变化的那一侧在 CI 由 `--build=missing` 源码重建——选 2.12.1 要重建 glibmm（291 个 ninja 目标），实测 CI worker 反复 `ninja: fatal: posix_spawn: Resource temporarily unavailable`（fork/EAGAIN 进程数耗尽，5 次 CI 里 4 次因此红）；选 2.10.8 只重建 cairomm+pangomm（约 80 个目标，且二者 build() 都不跑 meson test），glibmm 复用已发布 binary |
| 3 | meson configure 失败：`Could not get pkg-config variable and no default provided for <PkgConfigDependency glibmm-2.4>` | gtkmm `meson.build:164/166/168` 无条件读 `gmmprocdir` / `gmmprocm4dir`；PkgConfigDeps 依据 cpp_info 重新生成 .pc，上游安装的这几个变量丢失 | `_inject_gmmproc_pc_variables()`：向生成的 glibmm-2.4/giomm-2.4.pc 注入 `gmmprocdir=<glibmm 包>/lib/glibmm-2.4/proc`，向 pangomm-1.4/atkmm-1.6.pc 注入 `gmmprocm4dir=<包>/lib/<pkg>/proc/m4`（与上游 .pc 同值） |
| 4 | meson configure 失败：`Could not get pkg-config variable ... <PkgConfigDependency gio-2.0>`（demos/gtk-demo） | `demos/gtk-demo/meson.build` 仅以 `epoxy_dep.found()` 守卫，而 libepoxy 经 gtk/3.24.43 传递存在于图中 → `-Dbuild-demos=false` 仍配置 demos，其 `gnome.compile_resources()` 需要 gio-2.0.pc 的 `glib_compile_resources` | 补丁 `0001-gate-demos-on-build-demos.patch`：`subdir('demos/gtk-demo')` 以 `build_demos` 守卫（同 gtkmm 4.0.0 recipe 的 0002 补丁） |
| 5 | `Library glibmm_generate_extra_defs-2.4 found: NO` → configure 失败 | `tools/extra_defs_gen` 用 `cpp_compiler.find_library('glibmm_generate_extra_defs-2.4')`（无 dirs 参数）；glibmm 包只声明 glibmm-2.4/giomm-2.4 组件，不生成该工具库的 .pc/-L | `_fix_glibmm_generate_extra_defs_lib()`：把 glibmm 包 libdir 前置到 `LIBRARY_PATH`，clang 将其翻译为 `-L`（同 gtkmm 4.0.0 recipe） |
| 6 | `gtk+-unix-print-3.0` 依赖找不到 / Cflags 指向不存在的目录 | 非 Windows 分支硬性 `dependency('gtk+-unix-print-3.0')`；PkgConfigDeps 只生成 `gtk+-3.0.pc`，gtk 包自带的该 .pc prefix 是构建机 conan cache 路径 | `_fix_gtk_unix_print_pc()`：从 gtk 包拷入 generators 目录并把 `prefix=` 重写为 gtk 包根 |
| 7 | object_move_test 真实失败 `Gtk-WARNING: cannot open display`（exit 1） | 该测试调用 `gtk_init()`；OHOS 无窗口系统（Broadway 亦无法启动 server），`GDK_BACKEND=broadway` 实测同样失败 | 补丁 `0002-failing-suite-for-display-dependent-tests.patch` 标记 failing suite，`build()` 用 `--no-suite=failing` 排除；gdk_rgba_test 无窗口依赖，真实执行（与 glibmm 2.66.9、gtkmm 4.0.0 同款处理） |
| 8 | glibmm 从源码重建时 `meson test` 33 项中 31 项 `exit status 127`（`g_libintl_*: symbol not found`） | 本机装有 gettext（`/storage/Users/currentUser/usr/local/lib/libintl.so.8`，导出 `libintl_*`），在 LD_LIBRARY_PATH 中排在 glib 包 lib 之前，遮蔽 glib 包内 vendored proxy-libintl（导出 `g_libintl_*`）——**环境专属陷阱，非配方缺陷**（见 `knowledge/drafts/DRAFT-glib-2.84.0.1-gettext-libintl-ld-library-path-shadow.kv`） | 本地 W3 运行时把 glib 包 libdir 前置到 `LD_LIBRARY_PATH`（干净环境/CI 无此问题）；配方不改、glib 不升版 |
| 9 | 本机 `meson` 命令不可用（`meson: inaccessible or not found`） | worker 的 `/storage/Users/currentUser/usr/local/bin/meson` 被改名为 `meson.broken-worker-shadow`，其 shebang 指向已移除的 el2 bundle python | 本地修复：恢复该路径下的 shim，用持久 user python3 `-m mesonbuild.mesonmain`（**不能用 `python -c`**——meson 用 `meson_command` 自我重入做 symbolextractor，`-c` 会让 ninja 去 exec `<builddir>/-c`）。属 worker 环境修复，不入 PR |

## 源码修改

无源码行为修改，仅两个构建/测试门控补丁：

| 补丁 | 内容 | 理由 |
|------|------|------|
| `0001-gate-demos-on-build-demos.patch` | `meson.build`：`subdir('demos/gtk-demo')` 以 `build_demos` 守卫 | demos 的 `epoxy_dep.found()` 守卫在 Conan 图中恒真（libepoxy 传递存在），`build-demos=false` 失效；且 demos 需 glib 构建期工具变量 |
| `0002-failing-suite-for-display-dependent-tests.patch` | `tests/meson.build`：`object_move_test` 注册进 `failing` suite | 该测试需 `gtk_init()`，OHOS 无窗口系统下真实失败；suite 由 `--no-suite=failing` 排除，测试程序仍构建 |

## 依赖版本

- libsigc/2.10.8（override；对齐 glibmm 的 pin，sigc++-2.0，SONAME `libsigc-2.0.so.0`）
- glibmm/2.66.9（glibmm-2.4 + giomm-2.4；复用制品仓已发布 binary，绑定 libsigc/2.10.Z）
- gtk/3.24.43（gtk+-3.0 + gtk+-unix-print-3.0，Broadway-only）
- atkmm/2.28.4（atkmm-1.6）
- cairomm/1.14.5.1（cairomm-1.0；因 libsigc 对齐由源码重建，约 40 个目标，无 meson test）
- pangomm/2.46.5（pangomm-1.4；因 libsigc 对齐由源码重建，约 30 个目标，无 meson test）
- gdk-pixbuf/2.44.6.1（gdk-pixbuf-2.0；与 gtk/3.24.43 的 pin 一致）
- 传递：glib/2.84.0.1、cairo/1.18.4、cairo-gobject/1.18.4.2、pango/1.50.14.1.1、
  atk/2.38.0.1.1、harfbuzz/14.2.0、fribidi/1.0.16、libepoxy/1.5.10、
  fontconfig/2.18.1.1、freetype/2.14.3、pixman/0.46.4、libpng/1.6.58、
  zlib/1.3.1.1、libffi/3.4.4、pcre2/10.45、expat/2.8.2.1.1 等

## 验证结果

```bash
# 1) conan create（W3/CI 同源）
conan create archives/g/gtkmm/3.24.11 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# → Package 'c0f0bb739ec3ca8feec0dbd044bcfefdb3c15ec6' created  (exit 0)

# 2) 上游测试（meson test，build() 内执行）
meson test -v -C <build> --timeout-multiplier=16 --no-rebuild --no-suite=failing
# → 1/1 gtkmm:gdk_rgba_test OK 0.12s ; Ok: 1  Fail: 0
#   （object_move_test 因无窗口系统真实失败，已归入 failing suite 不执行，仅构建）

# 3) test_package 消费者测试（原生 OHOS 运行）
# → gtkmm-3.0 probe: checks=11 PASS

# 4) 产物
# lib/libgtkmm-3.0.so.1.1.0  lib/libgdkmm-3.0.so.1.1.0
# include/gtkmm-3.0  include/gdkmm-3.0  lib/pkgconfig/{gtkmm-3.0,gdkmm-3.0}.pc
```

详细证据见 `reports/test-report.md`。

## 注意事项

- **ABI 线不可混用**：gtkmm-3.0 必须配 glibmm-2.4 / cairomm-1.0 / pangomm-1.4 /
  atkmm-1.6 / sigc++-2.0；误配 glibmm-2.68 等 4.0 线依赖会在 meson
  `dependency()` 阶段即失败。
- **libsigc override 副作用**：CI 构建本包时会从源码重建
  cairomm/1.14.5.1 与 pangomm/2.46.5（包 id 因 libsigc 版本对齐而变化），
  glibmm/atkmm 复用已发布 binary；两者合计约 80 个 ninja 目标、无 meson
  test，属预期且代价可控。
- **本机 gettext 遮蔽**：本机 `/storage/Users/currentUser/usr/local/lib` 的
  gettext `libintl.so.8` 会遮蔽 glib 包内 vendored proxy-libintl，导致
  `g_libintl_*: symbol not found`；W3 需把 glib 包 libdir 前置到
  `LD_LIBRARY_PATH`。CI 干净环境不受影响。
- **无 X11 API**：`build-x11-api=false`，Gdk::X11 相关 API 不提供（平台无
  X11 后端），如需可改用 4.0 线的 gtkmm。

- **R40 图形域适配完整性（需人工确认）**：gtkmm 是 GTK 的 C++ 绑定层，自身不含
  渲染实现；OHOS 无窗口系统（`gtk_init()` 不可用、Broadway server 无法启动），
  窗口/渲染路径无法在本包内验证，渲染能力完全由 `gtk/3.24.43`（Broadway-only）
  提供。test_package 覆盖的是无显示依赖路径（Gdk::RGBA / Gdk::Rectangle /
  GType / sigc++ 信号）。Gdk::X11 API 明确不提供（`build-x11-api=false`）。

**编译结束**: 2026-10-15
**最终状态**: built
---

**编译结束**: 2026-10-15 11:50
**最终状态**: built
