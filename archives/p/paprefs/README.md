# paprefs 1.2 — PulseAudio Preferences

PulseAudio 音频服务器/网络配置对话框（GTK GUI，C++/gtkmm）。

## HarmonyOS PC 适配要点

| 问题 | 处理 | 出处 |
|---|---|---|
| glib proxy libintl.h 把 gettext 家族改名为 g_libintl_*，OHOS 无符号提供 | gettext/0.22.5.1 + 配方自带 `res/intl-wrapper.c`（g_libintl_* → libintl_* 转发） | E508 / ohos-nls-libintl |
| gtk/3.24.43 为 Broadway-only（无 X11 后端） | `GDK_WINDOWING_X11` 守卫 gdkx.h 与 GDK_WINDOW_XID | patches/0003 |
| OHOS 运行时拒绝未签名 .so | 配方 package() 对 bin/lib 产物 codesign；测试端对缺签依赖库临时补签 | E135 |
| pulseaudio 包不带 org.freedesktop.pulseaudio.module-group schema | 测试端生成最小 schema 并 glib-compile-schemas 编译注入 | test_package/conanfile.py |

## 使用

```sh
# 依赖已由 conan 图管理，直接运行
paprefs
```

GUI 运行需要显示后端（OHOS 上经 broadwayd）与 D-Bus session。
