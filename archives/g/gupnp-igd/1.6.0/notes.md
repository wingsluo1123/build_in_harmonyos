# gupnp-igd 1.6.0 — 适配笔记

- 上游：https://gitlab.gnome.org/GNOME/gupnp-igd（GNOME，LGPL-2.1-or-later）
- 源码：官方发布 tar.xz（NJU 镜像 + GNOME 官方双源，sha256 实测一致）
- 构建：meson + ninja，产物 `libgupnp-igd-1.6.so.0.0.0` + 头文件
  `include/gupnp-igd-1.6/libgupnp-igd/`，pkg-config 名 `gupnp-igd-1.6`

## 与上游构建系统的差异

1. `-Dintrospection=false`：上游 meson_options.txt 中 introspection 默认
   `true`（gupnp-igd 1.6.0 仅有的两个选项之一），交叉编译没有
   gobject-introspection 原生工具，必须显式关闭；`-Dgtk_doc=false` 与上游
   默认一致，显式钉死。
2. `subprojects/gupnp-1.6.wrap` 删除：tarball 携带 [wrap-git] 包装（钉
   gupnp-1.6.3，无 [provide] 段），meson 在 pkg-config 可解析 gupnp-1.6 时
   不会回退子项目，但为杜绝 CI Worker 任何运行时 git clone 可能性，配方
   在 source() 阶段整体删除 subprojects/ 目录。
3. 无源码补丁：两个 C 翻译单元（gupnp-simple-igd.c、
   gupnp-simple-igd-thread.c）的网络头仅 arpa/inet.h、netinet/in.h、
   sys/types.h、sys/socket.h、string.h，在 OHOS musl sysroot 全部可用；
   不像 gupnp/gssdp 需要 netlink 探测加固（gupnp-igd 不碰 netlink）。

## GObject 单副本（继承 gssdp 1.6.6 / gupnp 1.6.10 教义）

ohpcd 制品仓只发布了静态 glib2。若 GLib 系 .pc 的 `Libs: -lglib-2.0 ...`
按原样进入链接，静态 glib 被链进 libgupnp-igd-1.6.so，加上
libsoup-3.0.so 自带副本 → GObject 双副本 GType 注册撕裂 SIGABRT。

修法（与 gssdp/gupnp 同款）：
- glib2 包 .pc 复制件（pc-fix）：prefix 修到真实 package_folder、Libs 置
  空、Requires 剔除 libffi（其前缀损坏，`-L//lib` 设备不可解析）；
- PkgConfigDeps 生成的 generators/glib-2.0.pc：Libs/Requires 置空；
- 生成的 libsoup-3.0.pc / gssdp-1.6.pc / gupnp-1.6.pc / libxml-2.0.pc：
  token 级剔除静态 glib 链接列表（保留 -lsoup-3.0/-lgssdp-1.6/
  -lgupnp-1.6/-lxml2 与系统库，Requires 闭包保留）。

结果：libgupnp-igd-1.6.so 对 g_* 全部 UND，运行时统一解析到
libsoup-3.0.so 导出的唯一 gobject 副本。

## 为什么不需要 glib-min 补链归档（与 gupnp 1.6.10 的差异）

gupnp 1.6.10 需要 libglib-min.a 是因为它调用了两个 libsoup-3.0.so 未导出
的 glib/gio API（g_uuid_string_random、g_zlib_compressor_new）。
gupnp-igd 1.6.0 的源码符号核验（nm 对照已发布栈）：
- g_warning → 宏，展开为 g_log（libsoup-3.0.so 导出）；
- g_atomic_int_set / g_atomic_int_dec_and_test → glib 头内 static inline；
- 其余 58 个 g_* 函数（g_main_context_*、g_object_*、g_signal_*、
  g_source_*、g_ptr_array_*、g_cond_*、g_mutex_*、g_thread_*、
  g_cancellable_*、g_inet_address_* 等）全部由 libsoup-3.0.so 导出
  （实测 4086 个 g_* 导出符号）。
故本配方不带最小补链归档，也不需要 zlib 直接参与（zlib override 仅用于
钉住静态 glib2 链的 PIC 变体，继承同族配方）。

## 构建工具细节（同族先例复用）

- CI Worker 导出 AR/AS/STRIP/NM/RANLIB 为 llvm-* 名且不在 PATH：generate()
  里弹出环境值并用绝对路径钉住 GNU 工具；
- `tc.strip = None`：strip 会改写 .so 破坏 .codesign 内嵌哈希 → dlopen
  Permission denied（libsoup3 本地铁证）；
- package() 用 build 树原始链接产物覆盖 install 出来的 .so：meson install
  会清理 DT_RUNPATH 使 .codesign 哈希失配；
- gnome.genmarshal() 需要 glib2 包 bin/ 的 glib-genmarshal：PATH +
  tc.binaries 双保险钉死；
- meson_layout 在 conan 2.29 被移除：手动 layout()（builddir /
  builddir/generators）。

## 依赖清单（对齐制品仓已发布版本）

| 依赖 | 版本 | 用途 |
|------|------|------|
| glib2 | 2.88.0 | glib/gobject/gthread 模块 + glib-genmarshal 工具 |
| libsoup3 | 3.6.5-r1 | GObject 单副本载体（g_* 符号导出方） |
| gssdp | 1.6.6 | SSDP 发现层（gupnp 的传递闭包，pc Requires 引用） |
| gupnp | 1.6.10 | UPnP 协议栈核心（meson 直接依赖 gupnp-1.6 >= 1.6.0） |
| libxml2 | 2.15.3.1 | gupnp-1.6.pc 的 Requires 闭包成员 |
| zlib | 1.3.1.1（override） | 静态 glib2 链的 PIC 变体钉扎 |

## 上游测试

- `tests/gtest/gupnp-simple-igd.c`：meson test 1 项（glib TAP 框架），
  11 个 TAP 子用例（new/default_ctx/remove_local/custom_ctx/thread/
  random-no_conflict/random-conflict/dispose_removes-regular/
  dispose_removes-thread/invalid_ip/empty_ip），模拟 IGD 设备走回环
  （SSDP 发现 + SOAP 动作往返），is_parallel: false，XML_PATH 环境指向
  测试目录；
- build() 在 OHOS 设备原生跑 meson test（--timeout-multiplier=48，1440s
  ——CI 高载 Worker 实测 480s 不够用：构建 #93350 在 480.03s 被 SIGTERM
  杀死，本地空载约 1-2 分钟跑完；1440s 仍在 conan create 默认 3600s 预算
  内），交叉编译（CI Linux Worker）跳过；
- tests/examples 为 demo 程序（不 install），随库一起构建不随包发布。
