# DRAFT-xmedcon-conan-graph-gtk-zlib-pin：gtk3 闭包库（zlib/libpng）版本必须与 glib/gdk-pixbuf 的 pin 对齐，否则 G2 版本冲突

> Source: xmedcon/0.26.1-gtk3 适配 W0/W2（本机 conan graph info 验证）
> 对应 KV: knowledge/drafts/DRAFT-xmedcon-conan-graph-gtk-zlib-pin.kv

## 一句话

任何依赖 `gtk/3.24.43` 的包，若额外直接声明 `libpng`/`zlib`，其版本必须取
`libpng/1.6.58`（→zlib/1.3.1.1）与 `zlib/1.3.1.1`，与闭包内 `glib/2.84.0.1 → zlib/1.3.1.1`、
`gdk-pixbuf/2.44.6.1.1 → libpng/1.6.58` 对齐；选新版（如 libpng/1.6.58.3 → zlib/1.3.2、
zlib/1.3.2.1）会让 G2 在两个旧 pin 之间报版本冲突。

## 冲突链（实测）

- `libpng/1.6.58.3` requires `zlib/1.3.2`；`glib/2.84.0.1` requires `zlib/1.3.1.1`
  → `Conflict between zlib/1.3.2 and zlib/1.3.1.1 ... originates from glib`。
- `zlib/1.3.2.1` 与 `libpng/1.6.58.3` 之间同样冲突（originates from libpng）。
- 修正组合 `zlib/1.3.1.1 + libpng/1.6.58 + gtk/3.24.43` → `conan graph info` 全图解析无冲突。

## 使用说明

```powershell
# 配方写完后、上真机前，在本机用任一 profile 做纯图验证（不需要二进制）:
conan graph info archives/<首字母>/<库>/<版本> -pr default
# 出现 Conflict 时按 "Conflict originates from <pkg>" 提示逐级下钻，
# 用 Select-String 查各依赖配方里的 zlib/libpng pin，取闭包交集版本。
```

## 适用范围

- 所有 gtk3/gtk2 系 GUI 应用包（gtk/3.24.x、glib/2.84.x 闭包）需要直连 libpng/zlib 的场景。
- 不适用：不共享该闭包的独立包，可自由选新版本。

## 输入 / 输出

- 输入：conanfile.py 的 requires 列表。
- 输出：`conan graph info` 无 Conflict 的版本组合。

## 实证（2026-10-13，xmedcon/0.26.1-gtk3）

- r0：`zlib/1.3.2.1 + libpng/1.6.58.3` → 双冲突（glib、libpng 各一次）。
- r1：改为 `zlib/1.3.1.1 + libpng/1.6.58` → 图通过，依赖 glib/gtk/libpng/zlib + 构建依赖
  autotools-dev/pkgconf 全部 Cache/Download 命中。
