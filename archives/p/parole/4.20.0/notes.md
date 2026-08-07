# parole 4.20.0 编译笔记

## 基本信息
- 软件: parole (XFCE媒体播放器)
- 版本: 4.20.0
- 构建系统: meson
- 源码: https://github.com/xfce-mirror/parole/archive/refs/tags/parole-4.20.0.tar.gz
- SHA256: f44d0c314440da414ab10e6e8681285b8264e9d0f65f9cc47bc748ea93e46836
- 状态: **built** (conan配方已创建，构建验证因依赖缺失未通过)

## 依赖分析

### 必需依赖 (meson.build 硬依赖)
| 依赖 | pkg-config名 | 制品仓 | cmd-pkg | 状态 |
|------|-------------|--------|---------|------|
| glib | glib-2.0 | ✅ glib/2.84.0.1 | ✅ glib 2.88.0 | 可用 |
| GTK3 | gtk+-3.0 | ❌ | ❌ (3.24.38下载404) | **缺失** |
| D-Bus | dbus-1 | ❌ | ✅ dbus 1.14.10 | cmd-pkg可用 |
| dbus-glib | dbus-glib-1 | ❌ | ❌ | **缺失** |
| GStreamer | gstreamer-1.0 | ❌ | ✅ gstreamer 1.28.3 | cmd-pkg可用 |
| libxfce4ui | libxfce4ui-2 | ❌ | ❌ | **缺失** |
| libxfce4util | libxfce4util-1.0 | ❌ | ❌ | **缺失** |
| xfconf | libxfconf-0 | ❌ | ❌ | **缺失** |

### 可选依赖 (通过meson选项禁用)
| 依赖 | meson选项 | 处理 |
|------|----------|------|
| taglib_c | -Dtaglib=disabled | 已禁用 |
| libnotify | -Dnotify-plugin=disabled | 已禁用 |
| Wayland | -Dwayland=disabled | 已禁用 |
| X11 | -Dx11=enabled | 已启用 |

### GStreamer子包 (通过gst-plugins-base提供)
- gstreamer-base-1.0, gstreamer-video-1.0, gstreamer-audio-1.0, gstreamer-pbutils-1.0, gstreamer-tag-1.0

## Conan配方
- conanfile.py: 已创建，使用Meson构建系统
- conandata.yml: 已创建，SHA256已填写
- test_package/: 已创建，含CMakeLists.txt + test.c + MANIFEST.yml
- commands.json: 已创建(应用类型，含parole可执行文件声明)

## 构建验证
- conan create 未通过：依赖缺失(gtk3, dbus-glib, libxfce4ui, libxfce4util, xfconf未发布到制品仓)
- 原因：这些库均未适配到OHOS制品仓，需要先适配发布底层依赖

## 依赖链分析
```
parole
├── glib (制品仓有) ✅
├── gtk3 (制品仓无) ❌ → 需适配
│   ├── glib ✅, cairo ✅, pango ✅, gdk-pixbuf ✅
│   ├── atk ✅, harfbuzz ✅, freetype ✅, fontconfig ✅
│   └── libepoxy ✅, egl ✅
├── dbus (制品仓无, cmd-pkg有) → 需适配到制品仓
├── dbus-glib (制品仓无) ❌ → 需适配
│   └── dbus, glib
├── gstreamer (制品仓无, cmd-pkg有) → 需适配到制品仓
├── libxfce4util (制品仓无) ❌ → 需适配
│   └── glib
├── xfconf (制品仓无) ❌ → 需适配
│   └── glib, dbus
└── libxfce4ui (制品仓无) ❌ → 需适配
    └── gtk3, libxfce4util, xfconf
```

## 平台问题
1. HMDFS不支持execute权限，导致meson setup时sanity check失败
2. OHOS SDK的lld链接器依赖libxml2.so.16但无法正确加载
3. 需使用`-fuse-ld=bfd`绕过lld问题

---
**编译结束**: 2026-08-07
**最终状态**: built (conan配方已创建，依赖链缺失待解决)
