# pqmarble

GNOME **Marble**（Debian 包名 `pqmarble`）是一个给 Gtk 应用复用的通用组件库，
由 Paulo Queiroz（raggesilver）维护，Vala 编写、导出 C ABI 共享库。

- 上游仓库: <https://gitlab.gnome.org/raggesilver/marble>
- 本版本源码: tag `v1.3.0`（commit `710a677a`）
- 产物:
  - `lib/libmarble.so.1.3.0`（SONAME `libmarble.so.1`）
  - `include/marble.h`（valac 生成的 C 头）
  - `share/vala/vapi/marble.vapi`、`marble.deps`（Vala 消费者使用）
  - `share/gir-1.0/Marble-1.3.0.gir`
  - `lib/pkgconfig/marble.pc`

## 提供的 API

| 类型 | 说明 |
|------|------|
| `Marble.SideWindow` | 带侧栏的 `Gtk.ApplicationWindow` |
| `Marble.Loadable` | 带 `Gtk.Spinner` 遮罩的 `Gtk.Overlay` |
| `Marble.Progressable` | 带 `Gtk.ProgressBar` 遮罩的 `Gtk.Overlay` |
| `Marble.Settings` | 基于 `GLib.Settings` 的属性绑定基类（抽象类） |
| `Marble.get_css_provider_for_data()` / `set_theming_for_data()` | CSS 主题工具 |

## 构建

```bash
conan create archives/p/pqmarble/1.3.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64
```

依赖：`glib/2.84.0.1`、`gtk/3.24.43`（GTK3，OHOS 侧为 broadway 后端）；
构建工具：`meson/1.11.0`、`ninja/1.12.1`、`vala/0.56.19`、`pkgconf/3.0.6`。

## OHOS 适配要点

见 `1.3.0/notes.md`；核心是 valac vapi 路径归位、meson machine file 显式声明
构建工具、conan 包内 ELF 工具与产物 `.so` 自签名，以及 GLib GIR 缺失时关闭
`.typelib` 生成（`.gir`/`.vapi` 仍由 valac 正常产出）。
