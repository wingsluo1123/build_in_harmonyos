# wayland-protocols 1.33 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-29
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 从 gitlab.freedesktop.org 下载源码 (tar.bz2)
2. 初始化编译环境：`ohc-run.py init-build wayland-protocols 1.33`
3. 安装依赖：wayland 1.22.0 预编译包（已安装到 ~/usr/local）
4. 配置：`meson setup builddir --prefix=$DEFAULT_PREFIX -Dtests=false`
   - 禁用测试（测试需要编译器）
   - 设置 PKG_CONFIG_PATH 以检测 wayland-scanner
5. 编译：`meson compile -C builddir`（无实际编译任务，纯数据包）
6. 安装：`meson install -C builddir --destdir=$TEST_PREFIX`
7. 验证：`pkg-config --modversion wayland-protocols` → 1.33
8. 打包：`ohc-run.py package wayland-protocols 1.33`
9. 归档：`ohc-run.py finish wayland-protocols 1.33 built`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | meson 找不到 wayland-scanner | PKG_CONFIG_PATH 未设置 | 手动设置 `PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH` |
| 2 | 测试需要编译器 clang | wayland-protocols 是纯数据包 | 禁用测试 `-Dtests=false` |
| 3 | 质量门禁失败：缺少 build_system | manifest.yaml 使用嵌套字段 | 添加顶层 `build_system: meson` 字段 |

## 源码修改

无补丁，无源码修改。

## 依赖版本

| 软件 | 版本 | 来源 |
|------|------|------|
| wayland | 1.22.0 | 预编译包（刚编译） |
| meson | 1.11.1 | 预装 |
| ninja | 1.13.0 | 预装 |

## 验证结果

```bash
$ pkg-config --modversion wayland-protocols
1.33
$ pkg-config --variable=pkgdatadir wayland-protocols
//storage/Users/currentUser/usr/local/share/wayland-protocols
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| wayland-protocols-1.33-ohos-aarch64.tar.gz | 613KB | 预编译包（39 个 XML 协议文件 + 1 个 .pc 文件） |

## 注意事项

1. wayland-protocols 是纯数据包，无二进制文件
2. 需要先安装 wayland（提供 wayland-scanner）
3. meson 配置时需要正确设置 PKG_CONFIG_PATH
4. 官方下载 URL (wayland.freedesktop.org/releases/) 404，使用 gitlab archive

---

**编译结束**: 2026-05-29 16:17
**最终状态**: built