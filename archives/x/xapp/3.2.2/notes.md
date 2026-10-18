# xapp 3.2.2 适配笔记（2.8.9 基线升级移植）

## 移植定性

本版本为**版本升级移植**：以同仓 archives/x/xapp/2.8.9 配方为基线（该 run
五轮 CI 换来的全部硬约束直接沿用，不重新试错），3.2.2 的上游 DELTA 极小，
配方除版本号/证据文案外零逻辑改动。

## 编译环境
- 构建系统: meson（上游 meson_version >= 0.56.0 不变；CI 机 meson 1.5.1）
- 编译日期: 2026-10-10
- 编译器: clang（/data/service/hnp/bin，llvm 15 工具链，target
  aarch64-unknown-linux-ohos）
- 依赖（与 2.8.9 基线完全一致，全部 ohpcd 已发布）:
  gtk/3.24.43（OHOS shared broadway-only，glib/2.84.0.1 pin 链）、
  libx11/6.4.0、libxkbfile/1.1.3、dbus/1.14.10.1

## 2.8.9 → 3.2.2 上游 DELTA（Builder 对打包源逐字节复核）

| 面 | 结论 | 证据 |
|----|------|------|
| 根 meson.build | 仅 version 行 2.8.9→3.2.2 | 全文 diff 仅 1 处 hunk |
| libxapp/meson.build | 逐字节一致 | diff 空输出 |
| libxapp/xapp-gtk-window.c | 逐字节一致 | diff 空输出 → 补丁零改动平移 |
| meson_options.txt | 逐字节一致 | diff 空输出 → 开关集照旧 |
| 唯一库代码变化 | xapp-gpu-offload-helper.c：新增 GVariant "Discrete" 键解析入私有 hash table | diff（实例内部字段 + 循环内 lookup，不导出新符号） |
| 其余变化 | debian/docs/po 文档 churn，不进构建面 | diff -rq 清单 |
| license | 不变（COPYING GPL-3 + COPYING.LESSER LGPL-3，库为 LGPL-3.0-or-later） | 归档内文件核对 |
| 补丁适用性 | 0001 对 3.2.2 树 git apply --check 干净适用 | 3.2.2 解包树 dry-run |

补丁与配置面细节（broadway-only 实证、C_SIGNALS-1 探针、开关→缺口映射）
直接沿用 2.8.9 笔记结论，此处不重复；两版 xapp-gtk-window.c 逐字节一致
意味着补丁上下文与行号完全有效。

## 配方层处理（全部自 2.8.9 平移，机理见 conanfile.py 注释与经验仓）

1. **dbus 钉 1.14.10.1**（dependency/xapp-2.8.9-dbus-revision-pin-alignment.md）：
   .2 拉 glib/2.88.3 对撞 gtk 的 glib/2.84.0.1 pin；.0 pin expat/2.8.2
   对撞 fontconfig 传递的 expat/2.8.2.1；.1 与 gtk3 生态完全对齐。3.2.2
   根 meson.build 的 dbus-1 get_variable 探测面不变（无 default_value）。
2. **g_libintl 链接闭包**（link-error/xapp-2.8.9-libintl-lld-search-order.md）：
   3.2.2 仍为 7 个 libxapp/*.c include glib/gi18n-lib.h（消费面不变），
   继续注入 glib 包 lib/libintl.so 绝对路径。
3. **别名 .pc 两件套**（build-system/xapp-2.8.9-alias-pc-gio-unix-dbus1.md）：
   dependency('gio-unix-2.0')（libxapp/meson.build:4）与
   dependency('dbus-1')（根 meson.build:13）在 3.2.2 逐字节同位，合成逻辑照旧。
4. **gsettings schema DESTDIR 语义**（build-system/xapp-2.8.9-gsettings-schema-destdir.md）：
   schema 仍不编译随包分发（org.x.apps.favorites 的 "list" 键 type "as"
   default [] 不变），消费方（test_package）继续自编译。
5. 其余四件套（工具钉扎、conanbuildenv 追加、E077 自签名、strip=None、
   pristine .so 回填 + 签名）无版本敏感性，原样保留。

## 上游测试（NO_UPSTREAM_TESTS，discovery EVIDENCE_COMPLETE，对 3.2.2 重新取证）

| 口径 | 数量 | 证据 |
|------|------|------|
| tests/ 目录 | 无 | 3.2.2 解包树 ls 反证 |
| meson test() 注册 | 0 | 13 个 meson.build 逐文件 grep 'test(' 零命中 |
| test-scripts/ | 7 个脚本 | favorites/gpu-offload-helper/gtk-window/icon-chooser-dialog/kbd-layout-controller/status-applet/status-icon-variants——Python+gi 交互式 GUI 演示，未接入 meson |
| .github CI | 无测试步 | 唯一 workflow build.yml 委托 linuxmint do-builds.yml（build+codespell） |
| meson 测试开关 | 无 | meson_options.txt 与 2.8.9 逐字节一致 |

结论：无可执行的上游自动化用例 → NO_UPSTREAM_TESTS；鸿蒙特有消费者用例
沿用 2.8.9 的 test_package/test_xapp.c（20 项 TAP 断言，权威 CI 真跑），
并对 3.2.2 逐条复核有效性：
- 版本串断言 → CMakeLists 守卫改为 >= 3.2.2；
- X11 守卫断言（无 libX11 DT_NEEDED + NEEDED 闭包在 conan 图内）→
  补丁与 xapp-gtk-window.c 均未变，仍适用；
- pc closure（gtk+-3.0/gobject-2.0/cairo + Requires.private:xkbfile）→
  libxapp/meson.build pkg.generate 段逐字节一致，仍适用；
- dlopen/dlsym/mkenums 枚举断言 → xapp_enums mkenums 目标一致
  （xapp_scroll_direction_get_type 仍生成），仍适用；
- dlopen/libintl 断言（g_libintl_bindtextdomain 全局可解析）→ gettext
  消费面不变，仍适用；
- gsettings schema 断言 → org.x.apps.favorites "list" 键不变，仍适用。
- gpu-offload 新逻辑：编译进 libxapp 的内部实现，无新导出符号，不存在
  低成本纯逻辑断言面——不强加断言（MANIFEST.yml 已记录该判定）。

## 与本 run 相关的已知事实引用（附出处）

- 2.8.9 基线配方（同仓 archives/x/xapp/2.8.9/，含 notes.md 全部探针实证）
- 经验仓 dependency/xapp-2.8.9-dbus-revision-pin-alignment.md
- 经验仓 link-error/xapp-2.8.9-libintl-lld-search-order.md
- 经验仓 build-system/xapp-2.8.9-alias-pc-gio-unix-dbus1.md
- 经验仓 build-system/xapp-2.8.9-gsettings-schema-destdir.md
- skill references/build-chain-pitfalls.md（lld 隐式闭包定律 + 显式注入时机）
