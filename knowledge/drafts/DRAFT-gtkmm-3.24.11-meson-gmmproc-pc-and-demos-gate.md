# DRAFT-gtkmm-3.24.11-meson-gmmproc-pc-and-demos-gate：gtkmm 3.24（gtkmm-3.0 线）meson 配方：PkgConfigDeps 重建的 *mm .pc 丢失 gmmprocdir/gmmprocm4dir、demos 守卫失效、object_move 测试无窗口系统

> Status: **Draft**（待审核 promote）| severity: `2` | category: `build-system, meson, pkg-config, conan, compilation, testing` | Updated: 2026-10-15
> 对应: `knowledge/drafts/DRAFT-gtkmm-3.24.11-meson-gmmproc-pc-and-demos-gate.kv`

---

## 触发面

- trigger_tool: `conan|conan create|meson|pkg-config|meson setup`
- phase: `configure|compilation|testing`

**匹配关键词**：gtkmm, gdkmm, gtkmm-3.0, gmmproc, gmmprocdir, gmmprocm4dir, PkgConfigDeps, PkgConfigDependency, get_variable, epoxy, build-demos, build-x11-api, failing suite, no-suite=failing, meson

## 错误签名（error_signature）

```text
Could not get pkg-config variable and no default provided for <PkgConfigDependency (glibmm-2\.4|giomm-2\.4|pangomm-1\.4|atkmm-1\.6|gio-2\.0)|Library glibmm_generate_extra_defs.*not found|cannot open display
```

## 根因（root_cause）

gtkmm 3.24 官方 tarball 已迁移到 meson（无 `configure` 脚本；`init-build` 会按
URL/文件名误判 autotools）。与 Conan + OHOS 的交互有四处坑：

1. **gmmproc 变量丢失**：`meson.build:164/166/168` 无条件读取
   `glibmm_dep.get_variable('gmmprocdir')`、`pangomm_dep.get_variable('gmmprocm4dir')`、
   `atkmm_dep.get_variable('gmmprocm4dir')`。上游 `lib/pkgconfig/*.pc` 带这些变量，
   但 `PkgConfigDeps` 按 `cpp_info` 重新生成 .pc（只有 prefix/libdir/includedir/
   Libs/Cflags/Requires）→ meson 报 *Could not get pkg-config variable and no default
   provided for <PkgConfigDependency glibmm-2.4>*。
2. **demos 守卫失效**：`meson.build` 的 `subdir('demos/gtk-demo')` 无条件执行，
   而 `demos/gtk-demo/meson.build` 用 `epoxy_dep.found()` 守卫目标，
   `epoxy_dep = dependency('epoxy', required: build_demos)`。Conan 图中 libepoxy 经
   `gtk/3.24.43` 传递存在，PkgConfigDeps 生成 `epoxy.pc` → `found()` 恒真 →
   `-Dbuild-demos=false` 失效；demos 的 `gnome.compile_resources()` 又需要
   `gio-2.0.pc` 的 `glib_compile_resources`（同样不生成）→ configure 失败。
3. **extra_defs 工具库探测失败**：`tools/extra_defs_gen` 用
   `cpp_compiler.find_library('glibmm_generate_extra_defs-2.4')`（无 `dirs`），
   而 glibmm 包只声明 `glibmm-2.4`/`giomm-2.4` 组件，不提供该工具库的 `-L`。
4. **无窗口系统测试**：上游 `tests/meson.build` 注册执行的 `object_move_test` 调
   `gtk_init()`；OHOS 上 GTK+3 为 Broadway-only，无窗口系统（Broadway server 也无法
   启动，`GDK_BACKEND=broadway` 实测同样失败）→ `Gtk-WARNING: cannot open display`
   （exit 1）。

## 影响范围（affected_scope）

任何用 `PkgConfigDeps` + meson 构建的 `*mm` C++ 绑定库（gtkmm / glibmm / pangomm /
atkmm 系列），尤其 gtkmm-3.0 线；OHOS 无窗口系统平台必然命中第 4 条。

## 推荐方案（rec_approach: `inject-pc-tool-vars + gate-demos-subdir + failing-suite`）

1. `generate()` 中 `PkgConfigDeps(self).generate()` 之后注入工具变量：
   - `glibmm-2.4.pc` / `giomm-2.4.pc`：`gmmprocdir=<glibmm 包>/lib/glibmm-2.4/proc`
   - `pangomm-1.4.pc`：`gmmprocm4dir=<pangomm 包>/lib/pangomm-1.4/proc/m4`
   - `atkmm-1.6.pc`：`gmmprocm4dir=<atkmm 包>/lib/atkmm-1.6/proc/m4`

   （值与上游 .pc 一致；`maintainer-mode=false` 下仅作变量占位，不触发 gmmproc。）
2. 补丁 `meson.build`：`if build_demos` 包住 `subdir('demos/gtk-demo')`
   （同 gtkmm 4.0.0 recipe 的 `0002-gate-demos-on-build-demos.patch`）。
3. `build()` 中把 glibmm 包 `libdir` 前置到 `LIBRARY_PATH`，让 `find_library` 的
   link 探测命中 `libglibmm_generate_extra_defs-2.4.so`。
4. 补丁 `tests/meson.build` 把调 `gtk_init()` 的测试注册进 `failing` suite，
   `build()` 用 `meson test ... --no-suite=failing` 排除执行（测试程序仍构建），
   与 `glibmm/2.66.9` 配方同款处理。
5. `-Dbuild-x11-api=false`：既符合平台无 X11 后端，又规避 meson 读取 pkg-config 的
   `targets` 变量（PkgConfigDeps 同样不生成）。

参考实现：`archives/g/gtkmm/3.24.11/conanfile.py`。

## 验证方式（verification_cmd）

```text
conan create archives/g/gtkmm/3.24.11 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 期望：G2 conan create PASS；日志含 "1/1 gtkmm:gdk_rgba_test OK" 与
#       "gtkmm-3.0 probe: checks=11 PASS"
```

## 兜底（fallback）

无法注入变量时，可把依赖包 `lib/pkgconfig` 加入 `PKG_CONFIG_PATH` 让 meson 读到
上游自带 .pc——注意其 `prefix` 可能是构建机 cache 路径（甚至 `/`），需一并重写。

## 关联

- `kb_ref`: `E490`（autotools/meson 构建脚本相关）
- 同类配方：`archives/g/gtkmm/4.0.0.1`（gtkmm-4.0 线）、`archives/g/glibmm/2.66.9`
