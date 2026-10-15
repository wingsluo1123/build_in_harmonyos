# xapp 2.8.9 适配笔记

## 编译环境
- 构建系统: meson（上游 meson_version >= 0.56.0；CI 机 meson 1.5.1）
- 编译日期: 2026-10-09
- 编译器: clang（/data/service/hnp/bin，llvm 15 工具链，target aarch64-unknown-linux-ohos）
- 依赖（全部 ohpcd 已发布，R36/PF4 过）:
  gtk/3.24.43（OHOS shared broadway-only，glib/2.84.0.1 pin 链同 gtksourceview4/4.8.4）、
  libx11/6.4.0、libxkbfile/1.1.3、dbus/1.14.10.1
- 配方骨架: 派生 archives/g/gtksourceview4/4.8.4（同为 meson+gtk3 栈，
  _pin_build_env/_patch_conanbuildenv/_sign_glib_tools/_fix_glib_pcs/
  _augment_pcs_intl/_restore_unstripped_so/_sign_shared_libs 成品直接复用）。

## C_SIGNALS-1 探针结论（Builder 第一步，全部设备缓存实证）

探针对象：`~/.conan2/p/gtkcb2e1ae6c9dbc/p`（gtk/3.24.43，
package_id 18b354b6…，OHOS armv8 Release clang15 shared）：

1. `include/gtk-3.0/gdk/gdkx.h` **不存在**（目录清单 gdkbroadway.h 在、
   gdkx.h 无；`test -f` 反证 GDKX_H_ABSENT）→ 上游
   `xapp-gtk-window.c:11 #include <gdk/gdkx.h>` 直编必死。
2. `gdk/gdkconfig.h:13-17`：`#undef GDK_WINDOWING_X11` +
   `#define GDK_WINDOWING_BROADWAY` → `#ifdef GDK_WINDOWING_X11`
   是 GTK 自带的窗口系统守卫宏，broadway 构建下编译期即为假
   （gdk.h:30 包含 gdkconfig.h，守卫放在 `#include <gdk/gdk.h>` 之后即可）。
3. `readelf -d libgtk-3.so.0.2411.32`：DT_NEEDED **无 libX11**（broadway-only
   二进制），且含 `libintl.so.8`（proxy-libintl 实证）。
4. `GDK_WINDOW_XID` 宏在 broadway 头文件树中无定义（仅 gdkx.h 提供）→
   `get_window_xid()` 一并需要守卫。
5. `gdk_error_trap_push/pop_ignored` 在 `gdk/gdkmain.h:70-75` 可用
   （backend-agnostic），无需守卫。

### 补丁形态（patches/0001-gdk-windowing-x11-guard.patch）

- include 重排：`<gdk/gdk.h>` 提前（其内部含 gdkconfig.h），X11/Xatom/gdkx
  三个 include 移入 `#ifdef GDK_WINDOWING_X11`。
- `is_x11_session()`：守卫内 `GDK_IS_X11_DISPLAY(...)`，`#else` 分支
  `running_x11 = FALSE`（与上游非 X11 会话语义一致）。
- `set_window_hint_utf8 / set_window_hint_cardinal / get_window_xid` 三函数
  整体 `#ifdef`，`#else` 提供同签名 no-op/返 0 stub（xid 形参用 gulong，
  与公开 API `xapp_set_xid_*` 的 gulong 一致）——公开 API/ABI 不变，
  xapp_set_xid_* 仍导出，非 X11 下为 no-op（与上游 is_x11_session 运行时
  守卫等价的编译期形态）。
- 不引入任何 `__OHOS__` 类平台条件宏（R8）：守卫宏是 GTK 官方窗口系统宏，
  上游 lablgtk3 同款模式（compile-error/lablgtk3-3.1.5-x11-backend-macro-guard.md:34-35）。

## 构建开关（全部上游一等公民选项）

```
-Dapp-lib-only=true -Dintrospection=false -Dvapi=false -Dstatus-notifier=false -Ddocs=false
```

- 三缺口→开关映射（Scout-B DEP_GATE:none）：
  libgnomekbdui → app-lib-only（libxapp/meson.build:74-78）；
  pygobject-3.0 → introspection=false（根 meson.build:51-53；
  E179：OHOS 拒绝执行未签名自定义 ELF，g-ir-scanner 无法运行）；
  dbusmenu-gtk3-0.4 → status-notifier=false（xapp-sn-watcher/meson.build:35-36）。
- vapi 与 introspection 必须成对（libxapp/meson.build:149-150 assert）。

## 配方层的三个 OHOS 特有处理

1. **g_libintl 链接闭包（必做）**：libxapp 含 `glib/gi18n-lib.h`
   （xapp-favorites.c:15 等）→ bindtextdomain/dgettext 被重映射到
   g_libintl_*，唯一供给方是 glib 包 `lib/libintl.so`；PkgConfigDeps 重生成
   的 .pc 丢 -lintl，meson b_lundef 默认开 → 必挂。照抄 gtksourceview4
   `_augment_pcs_intl` 并按 libido3 范式加固（经验仓
   link-error/libido3-13.10.0-libintl-link-closure.md:31-32,43）：追加的是
   glib 包 lib/libintl.so 的**绝对路径**而非裸 `-lintl`。CI run-3 实证：
   pkg-config/meson 逐 .pc 独立展开，追加到 cairo.pc 的裸 -lintl 落在
   cairo/pixman/fontconfig/expat/freetype/libpng/zlib 的 -L 之后，lld 报
   "unable to find library -lintl"；绝对路径输入与位置无关。
2. **别名 .pc 合成**：meson 按文件名解析 `dependency('gio-unix-2.0')`
   （glib 配方无该组件）与 `dependency('dbus-1')`（dbus 配方注册名 dbus，
   且 xapp 根 meson.build:13-14 无 default_value 直接取
   session_bus_services_dir 变量）→ generate() 内合成 gio-unix-2.0.pc 与
   dbus-1.pc（后者注入 session_bus_services_dir=${datadir}/dbus-1/services）。
   不改 dbus/glib 上游配方（写入边界）。
3. **glib 宿主工具链四件套**（gdbus-codegen ×3 接口 + glib-mkenums）：
   绝对路径钉工具 + conanbuildenv 追加 NINJA/LD_LIBRARY_PATH + E077 工具
   自签名 + _fix_glib_pcs 注入 pc 工具变量（gtksourceview4 成品复用）。

## 上游测试（NO_UPSTREAM_TESTS，discovery EVIDENCE_COMPLETE）

| 口径 | 数量 | 证据 |
|------|------|------|
| tests/ 目录 | 无 | 全树 ls（Scout-A §4） |
| meson test() 注册 | 0 | 13 个 meson.build 逐文件 grep 'test(' 零命中 |
| test-scripts/ | 7 个脚本 | Python+gi 交互式 GUI 演示，未接入 meson，需真实显示 |
| .github CI | 无测试步 | 唯一 workflow build.yml 仅 build/package |
| meson 测试开关 | 无 | meson_options.txt 全文已核 |

结论：无可执行的上游自动化用例 → NO_UPSTREAM_TESTS；强制新增的鸿蒙特有
消费者用例落在 test_package/test_xapp.c（20 项 TAP 断言，权威 CI 真跑）：
xapp.pc 闭包（0.29.2 严格解析 Requires.private:xkbfile）、headless GType
注册、dlopen+g_libintl_bindtextdomain 全局解析（-lintl 闭包实证）、
产物无 libX11 DT_NEEDED（守卫生效）且 NEEDED 闭包在 conan 图内、
schema glib-compile-schemas 编译 + memory 后端 set/get 往返。全部不开显示
（E471/E527 纪律）。musl 事实（CI run-4 实证）：libxapp 自身 gettext 解析
走 musl libc/glib，--as-needed 下自身 DT_NEEDED 无 libintl，而 g_libintl_*
仍经 libglib 链全局可达（dlsym 断言）。

## 与本 run 相关的已知事实引用（附出处）

- E463.kv:15（无显示 runner + libffi ABI 陷阱 + 自签名）、E179.kv:9,16
  （ELF 签名 EPERM → introspection 关闭的真实依据）、
  E090.kv:17-20（meson host_system=harmonyos；本仓无该条件分支，仅知悉）、
  经验仓 compile-error/lablgtk3-3.1.5-x11-backend-macro-guard.md:34-35
  （broadway-only + gtkplug/gtksocket 头文件守卫实证）、
  link-error/libido3-13.10.0-libintl-link-closure.md:31-32,43
  （g_libintl 唯一供给方与绝对路径注入范式）、
  build-system/librsvg-2.62.3.md:19-20（cairo-gobject 假阳性教训——
  xapp libxapp 源不引 cairo_gobject_* 符号，经 gtk 传递的 cairo-gobject/1.18.4.2
  无需显式依赖；sn-watcher 面已关）、
  build-system/libido3-13.10.0-pkgconfig-vendored-pc-closure.md:40
  （pkg-config 0.29.2 对 Requires(.private) 成员的严格解析——本配方因此
  显式 require libxkbfile/1.1.3）。
