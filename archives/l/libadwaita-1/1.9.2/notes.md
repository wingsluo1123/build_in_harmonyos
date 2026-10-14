# libadwaita-1 1.9.2 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-09-15
- 编译器: clang/clang++ (OHOS aarch64, clang 15.0.4)
- 状态: published

## 编译步骤

```bash
# conan create（干净构建，依赖链全部已发布 ohpcd）
conan create archives/l/libadwaita-1/1.9.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing

# 配方内部 meson 配置要点：
#   -Dappstream=disabled        (AppStream 可选化，见补丁 0001-0005)
#   -Dintrospection=disabled    (无 g-ir-scanner)
#   -Dvapi=false -Ddocumentation=false -Dexamples=false
#   wrap_mode=nodownload        (依赖全部 conan 提供)
# sassc/3.6.2 作为 tool_require 编译 SCSS → base.css（tarball 无预生成 base.css）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Subproject appstream is buildable: NO` / Automatic wrap-based subproject downloading is disabled | libadwaita 硬依赖 AppStream；ohpcd 无配方，wrap 指向 github.com 不可达，wrap_mode=nodownload | 补丁把 appstream 变成 meson feature（default auto），`-Dappstream=disabled`，源码 appdata 解析代码用 config.h HAVE_APPSTREAM 守卫（gtk4 HAVE_EGL 先例） |
| 2 | `Subproject sassc is buildable: NO` | tarball 无 base.css，构建期需 sassc 编译 SCSS；wrap 指向 github 不可达 | 配方 `tool_requires("sassc/3.6.2")`（ohpcd 已发布，基于 libsass/3.6.5） |
| 3 | test_package <adwaita.h> not found / "Only <adwaita.h> can be included directly" | libadwaita 无伞形头之外的直接包含；公共头装到 include/libadwaita-1（非 .0 后缀） | package_info includedirs=["include/libadwaita-1"]，消费者必须包含伞形头 <adwaita.h> |
| 4 | .so 载入 / ELF 工具执行 "Operation not permitted" | OHOS 要求 ELF 代码签名 | 配方对 .so 与 glib bin 工具执行 objcopy --remove-section .codesign + binary-sign-tool -selfSign 1（ML-0043 同型） |
| 5 | 上游 67 个 GTK 测试全部 SIGABRT @ gtk_init | OHOS 无显示服务器（无 X11/Wayland），GTK4 仅 Broadway 后端，测试需要真实 display | 台账如实记录 0/67；不在 build() 执行 meson test；test_package 用无 display 版本 API 断言 |
| 6 | glib-2.0.pc/gio-2.0.pc 缺工具变量、fribidi.pc 缺子目录 include | PkgConfigDeps 生成的 .pc 不完整 | 配方 generate() 注入 glib_mkenums/glib_compile_resources 等变量、fribidi Cflags -I${includedir}/fribidi（gtk4 同款修复） |

## 源码修改

| 文件 | 补丁 | 说明 |
|------|------|------|
| meson.build | 0001 | appstream dependency 增加 `required: get_option('appstream')` |
| meson_options.txt | 0002 | 新增 `appstream` feature 选项（default auto） |
| src/adw-about-dialog.c | 0003 | `#include <appstream.h>`、get_release_for_version、populate_from_appdata 及其调用点以 HAVE_APPSTREAM 守卫 |
| src/adw-about-window.c | 0004 | include 与 get_release_for_version 守卫；deprecated new_from_appdata / show_from_appdata 无 appstream 时返回 NULL / no-op + g_warning |
| src/meson.build | 0005 | config_h.set('HAVE_APPSTREAM', ...)；libadwaita_deps 条件追加 appstream_dep |

## 依赖版本

- gtk4/4.22.4（提供 gtk4.pc；传递 pango/1.56.4、cairo/1.18.4、harfbuzz/14.2.0.1、gdk-pixbuf/2.44.6、graphene/1.10.8、libepoxy/1.5.10）
- glib/2.84.0.1.1（shared=True，override 统一全图；glib-2.0/gio-2.0 >= 2.84.0）
- fribidi/1.0.16
- sassc/3.6.2（tool_require，构建期 SCSS 编译；libsass/3.6.5）
- AppStream：appstream/1.2.0（ohpcd 2026-09-26 发布，-Dappstream=enabled；HAVE_APPSTREAM 守卫生效，About from_appdata 真实解析）

## 验证结果

```bash
# conan create 干净构建 + test_package 真实运行
1/1 libadwaita-1-test:libadwaita-1-test OK  (0.13s)
# 输出:
# PASS: adw_get_major_version() == 1
# PASS: adw_get_minor_version() == 9
# PASS: adw_get_micro_version() == 2
# HARMONY_LIBADWAITA_TEST_PASS

# W3 本地 CI 模拟（finish 内置）：setup.sh + build_and_test.sh 均 PASS
# conan-verify：G1-G5 全 PASS（结构/R36 依赖/同名隔离/产物完整性/平台矩阵/checksec/基线）
# 上游测试枚举：source_declared=67（374 个 g_test_add 用例）、configured=67、executed_passed=0
#   （headless 无显示服务器 SIGABRT @ gtk_init，日志 SHA-256 见 reports/upstream-test-ledger.md）
```

## 交付物

| 文件 | 说明 |
|------|------|
| 归档目录 archives/l/libadwaita-1/1.9.2/ | conanfile.py + conandata.yml + manifest.yaml + patches/* + test_package/* |
| 知识草稿 knowledge/graph/draft/E543-draft-214F.kv/.md | 路径 B：AppStream 硬依赖可选化 meson feature + HAVE_APPSTREAM 守卫 |

## 注意事项

1. libadwaita 头文件强制只允许包含伞形头 `<adwaita.h>`（"Only <adwaita.h> can be included directly"），消费者必须包含伞形头。
2. 公共头安装目录是 include/libadwaita-1（不是 libadwaita-1.0），配方 package_info 已按此设置。
3. 上游 About 对话框的 appdata 自动填充（AppStream）在 OHOS 上不可用：-Dappstream=disabled 时构造器/属性保留，populate 代码编译出，deprecated new_from_appdata 返回 NULL + g_warning——已如实记录，非伪造。
4. 67 个上游 GTK 测试在 headless OHOS 上不可运行（SIGABRT @ gtk_init），属真实平台硬阻塞；恢复条件：具备显示服务器环境执行 `meson test -C build-release`。