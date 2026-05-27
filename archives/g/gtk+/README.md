# GTK+ 3

GTK+ 3 (GIMP Toolkit) 是一个跨平台 GUI 工具包，用于创建图形用户界面。

## OpenHarmony 适配说明

- **构建系统**: meson
- **可用后端**: broadway (HTML5 渲染)
- **禁用后端**: X11, Wayland, Win32, Quartz（OpenHarmony 无相关显示协议支持）

### 编译配置

```bash
meson setup builddir --prefix=$DEFAULT_PREFIX \
  --native-file=meson-native.ini \
  -Dx11_backend=false -Dwayland_backend=false -Dbroadway_backend=true \
  -Dwin32_backend=false -Dquartz_backend=false \
  -Ddemos=false -Dexamples=false -Dtests=false \
  -Dintrospection=false -Dgtk_doc=false -Dman=false \
  -Dprint_backends=file -Dcolord=no
```

### 依赖

- glib >= 2.84.0
- pango >= 1.50.14
- cairo >= 1.18.4
- atk >= 2.58.3
- epoxy >= 1.5.10
- gdk-pixbuf >= 2.42.12
- harfbuzz >= 6.0
- fribidi >= 1.0.13

### 版本历史

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 3.24.43 | built | 2026-05-27 | 首次编译，1个补丁，broadway后端 |