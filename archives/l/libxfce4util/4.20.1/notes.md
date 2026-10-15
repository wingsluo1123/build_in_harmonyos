# libxfce4util 4.20.1 适配笔记

## 编译环境
- 构建系统: meson（XFCE 4.20 起上游以 meson 为主构建系统；tarball 同时携带
  autotools 文件但本配方走 meson）
- 编译日期: 2026-10-15
- 编译器: clang/clang++（OHOS SDK 26.0.0.18，aarch64-linux-ohos triplet）
- 状态: built

## 编译步骤

1. `conan create . -pr:h=/storage/Users/currentUser/.conan2/profiles/ohos-aarch64 --build=missing -c tools.build:jobs=2`
2. 配方要点（无源码补丁，全部在 conanfile.py 层适配）：
   - `PkgConfigDeps(self).generate()` 先行，随后增强 glib-2.0/gobject-2.0/gio-2.0.pc
     的 `Libs:` 行追加 `-lintl`（见下）；
   - `MesonToolchain`：`introspection=false`、`vala=disabled`、`gtk-doc=false`；
   - `tc.ar = /data/service/hnp/bin/ar`（meson 裸名探测 llvm-ar 在 CI worker 上
     ENOENT，wayland/glib 先例）；`tc.pkgconfig = shutil.which("pkg-config")`；
   - TMPDIR/TEMP 落到 build_folder/tmp（OHOS /tmp 只读）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | sysroot libc（链接期 stub）不导出 gettext 族符号；裸调 bindtextdomain/textdomain 链接报 undefined | OHOS sysroot 的 libintl.h 是空 stub，sysroot libc.so 不含 gettext 符号（设备运行时 libc 才有） | 编译期：glib 制品自带 proxy libintl.h（`#define gettext g_libintl_gettext` 等），meson dependency() cflags 使 glib include 目录先于 sysroot 命中，xfce-i18n.c/libxfce4util-private.c 的 gettext 调用全部宏替换为 g_libintl_*；链接期：`-lintl`（glib 包内 proxy-libintl，SONAME libintl.so.8）提供符号 |
| 2 | 消费 glib 共享库的目标链接失败 `undefined reference due to --no-allow-shlib-undefined: g_libintl_*` | OHOS lld 默认 `--no-allow-shlib-undefined`；libglib-2.0.so 有未定义 g_libintl_*，要求可执行文件链接行显式含 -lintl | 在 generate() 里对 conan(PkgConfigDeps) 生成的 glib-2.0/gobject-2.0/gio-2.0.pc 的 `Libs:` 行追加 `-lintl`（accountsservice 26.27.3 同款手法） |
| 3 | meson find_program('xdt-gen-visibility') 可能失败 | 该工具是源码根目录的 python3 脚本 | 实测 meson find_program 优先搜索源码目录，shebang `/usr/bin/env python3` 由构建环境 PATH 解析，无需处理 |
| 4 | meson 裸名探测 ar 报 ENOENT | CI worker PATH 上无裸名 llvm-ar | native file [binaries] 注入 ar=/data/service/hnp/bin/ar 绝对路径 |
| 5 | po/ 目录 gtk-doc 依赖 | i18n.gettext() 需要 msgfmt（严格模式） | OHOS worker PATH 上有 hnp msgfmt/xgettext 0.26，满足 i18n 模块；不满足时 meson 仅告警并跳过翻译目标（非致命） |
| 6 | docs/reference 的 gnome.gtkdoc / introspection 的 g-ir-scanner 不存在 | 制品仓无 gobject-introspection | `-Dgtk-doc=false`（默认即 false）+ `-Dintrospection=false` + `-Dvala=disabled` |
| 7 | 安装副本运行报 `Error loading shared library libxfce4util.so.7`（errno 为空，exit 127），后续全部符号 Error relocating | meson install 重写 ELF（剥离构建目录 RUNPATH）使链接器自签的 .codesign 段失效，OHOS 加载器拒绝加载；实测构建目录原件可正常加载运行 | package() 内对 lib/*.so* + bin/sbin 可执行 ELF 重签：llvm-objcopy --remove-section .codesign + binary-sign-tool selfSign（glib 2.84.0.1 / accountsservice 26.27.3 同款）；重签后 test_package 运行 PASS |
| 8 | test_package 收集依赖 include/lib 路径时 TypeError（package_folder=None） | conan 图中 libffi/pcre2/zlib 为 Skipped binaries（跳过的二进制节点无 package_folder） | 遍历 dependencies 时跳过 package_folder is None 的节点 |

## 源码修改

无（patches: {}）。

## 依赖版本

- glib/2.84.0.1（传递：libffi/3.4.4、pcre2/10.45、zlib/1.3.1.1，均在 ohpcd 制品仓）

## 验证结果

```bash
conan create . -pr:h=/storage/Users/currentUser/.conan2/profiles/ohos-aarch64 \
  --build=missing -c tools.build:jobs=2
# → RC=0
# test_package: test_libxfce4util PASS（9 组断言：版本/字符串/资源/许可证/变量展开/Kiosk）
# 上游无测试套件（N=0），见 test_package/MANIFEST.yml 审计声明
```

## 注意事项

- 本包是 XFCE 链根件（后续 libxfce4ui/libxfce4panel 等的前置），
  `package_info` 导出 pkg_config_name=libxfce4util-1.0，
  includedirs=include/xfce4（下游经 `#include <libxfce4util/libxfce4util.h>` 消费）。
- glib 依赖以 transitive_headers/transitive_libs 传播：下游消费者同样需要
  proxy libintl.h（编译期）与 -lintl（链接期），由 glib 组件闭包自动覆盖。
- xfce4-kiosk-query 可执行文件随 meson 默认构建产出（sbin/），静态链接场景
  上游 4.20.0 曾因 glib 符号未解析失败需跳过；4.20.1 meson 构建经 .pc 增强
  后 kiosk-query 正常链接（-lintl 已进 Libs 行）。
