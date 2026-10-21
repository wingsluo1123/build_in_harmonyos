# gnome-desktop

GNOME 桌面组件共用的工具库（Meson 构建）。提供壁纸/幻灯片背景、语言与区域匹配、
显示器布局（Mutter DisplayConfig D-Bus）、缩略图工厂、XKB 布局信息、空闲监视与
壁钟格式化等能力。

**官网**: https://gitlab.gnome.org/GNOME/gnome-desktop

**分类**: desktop/library

## 版本列表

- 44.1 (2026-10-17) - built（首次适配；legacy libgnome-desktop-3 + 上游测试实测）

## 依赖

- glib 2.84.0.1（gio-2.0 / gio-unix-2.0 / gobject-2.0）
- gdk-pixbuf 2.44.6.1
- gtk 3.24.43（legacy libgnome-desktop-3 需要）
- gsettings-desktop-schemas 49.1
- xkeyboard-config 2.48（XKB 规则数据）
- iso-codes 4.20.1（ISO-639/3166 数据与本地化语言名）
- fontconfig 2.18.1.1
- meson 1.11.0（tool_requires；本机/CI 均无系统 meson）

## 构建

```bash
conan create archives/g/gnome-desktop/44.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

默认选项：`shared=True`、`legacy_library=True`（库 libgnome-desktop-3）、
`build_gtk4=False`、`with_introspection=False`、`debug_tools=False`、
`with_tests=False`。

## 注意事项

1. `build_gtk4=True`（libgnome-desktop-4 / gnome-bg-4 / gnome-rr-4）当前**不可用**：
   gtk/3.24.43 与 gtk4/4.22.4 pin 不同 pango 版本，统一 override 后无已发布
   gtk3 binary（W0 实测）。需依赖侧先发布统一 pin 的 gtk3/gtk4 组合（R36）。
2. 同一依赖图内 gtk3 与 gtk4 并存会被 `validate()` 拒绝并给出原因。
3. OHOS 上 seccomp/bwrap 沙箱关闭（上游仅在 `host_machine.system()=='linux'`
   时启用），thumbnailer 脚本执行保留但无 seccomp 过滤。
4. 运行期数据路径（iso-codes、xkeyboard-config）在构建时以依赖包路径写入库
   （`ISO_CODES_PREFIX` / `XKB_BASE`）；XKB 可用 `XKB_CONFIG_ROOT` 覆盖。
5. 上游测试在 OHOS 真机实测 6/12 通过，失败项均为平台数据缺失
   （GLib 无 TZif 时区数据、无 libc locale 数据库、无显示后端），
   详见 `44.1/reports/test-report.md`（本地报告，不入库）与 `44.1/notes.md`。
