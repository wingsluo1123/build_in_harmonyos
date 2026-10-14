# E543 — AppStream 硬依赖可选化（meson feature + HAVE_APPSTREAM 守卫，libadwaita-1 on OHOS）

## 错误特征
上游 meson 项目（GNOME/GTK 生态）无条件声明 AppStream 依赖时，
头文件或子项目解析报错：

```
meson setup ... -Dwrap_mode=nodownload
ERROR: Automatic wrap-based subproject downloading is disabled
../src/stylesheet/meson.build:9:4: ERROR: Subproject appstream is buildable: NO
```
或直接：
```
Run-time dependency appstream found: NO (tried pkgconfig and cmake)
../meson.build:43:11: ERROR: Dependency "appstream" not found
fatal error: 'appstream.h' file not found
```
对应 .kv `error_signature`: `dependency('appstream')|Subproject appstream is
buildable: NO|wrap-git|github.com|appstream.h file not found`。

## 触发条件
- 构建系统: meson
- 阶段: configure / dependency-resolution
- 触发场景: OHOS（或同类无 AppStream 生态的平台）上的 GNOME/GTK 系库：
  - ohpcd 制品仓无 `appstream` 配方（2026-09 实测 0 命中）；
  - 上游 `dependency('appstream', fallback: ['appstream', ...])` 的 wrap
    指向 `github.com/ximion/appstream.git`，OHOS 构建环境 github 不可达；
  - 配方以 `wrap_mode=nodownload` 禁网（依赖全部由 conan 提供）。
- 对应 .kv `trigger_tool`: `meson|conan|GTK|libadwaita|gnome` / `phase`:
  `configure|dependency-resolution`。

## 根因分析
libadwaita-1 1.9.2 的 `meson.build` 无条件执行
`appstream_dep = dependency('appstream', fallback : ['appstream', 'appstream_dep'])`，
About 对话框（`src/adw-about-dialog.c`、`src/adw-about-window.c`）的
`populate_from_appdata` 直接调用 AppStream API（`as_metadata_new`/
`as_metadata_parse_file`/`as_component_get_releases_plain` 等）并
`#include <appstream.h>`。

OHOS PC 既没有已发布的 AppStream conan 配方，也够不到 gitlab/github 上的
上游源码（wrap 指向 github.com 不可达），因此 meson configure 在依赖解析
阶段必然失败。AppStream 在此类平台上属于“可选增强”而非核心功能
（仅影响 About 对话框从 appdata 元数据自动填充发行说明），适合编译期可选化。

## 解决方案

### 推荐方案
按“meson feature 选项 + config.h 守卫”把 AppStream 做成可选（沿用仓库内
gtk4/4.22.4 的 `HAVE_EGL` 守卫先例）：

1. **meson_options.txt**：新增 feature 选项
   `option('appstream', type: 'feature', value: 'auto', description: ...)`。
2. **meson.build**：`dependency('appstream', required: get_option('appstream'),
   fallback: [...])`——`-Dappstream=disabled` 时返回 not-found，不再触发
   wrap 下载或报错。
3. **src/meson.build**：`config_h.set('HAVE_APPSTREAM', appstream_dep.found())`
   生成 `config.h` 守卫宏；`libadwaita_deps` 仅在 `appstream_dep.found()` 时
   追加该依赖。
4. **源文件守卫**：`src/adw-about-dialog.c` 与 `src/adw-about-window.c` 的
   `#include <appstream.h>`、`get_release_for_version`、`populate_from_appdata`
   及其调用点全部 `#ifdef HAVE_APPSTREAM` 包裹；deprecated 公共 API
   `adw_about_window_new_from_appdata` / `adw_show_about_window_from_appdata`
   在无 AppStream 时 `return NULL` / 提前 return 并 `g_warning`（保持头文件
   声明与 ABI 完整）。
5. **配方**：`tc.project_options["appstream"] = "disabled"`；同时把构建期
   需要的 `sassc` 以 `tool_requires("sassc/3.6.2")` 提供（libadwaita 的
   SCSS→base.css 也走 github wrap，同类问题一并解决）。

### 禁止做法
- ❌ 伪造一个假的 `appstream.pc` / 空壳实现库蒙混 configure（R8 禁止空壳 stub）。
- ❌ 在补丁中直接写 `#ifdef __OHOS__` 平台宏而不提供实质逻辑（应使用
  `HAVE_APPSTREAM` 配置宏，与 gtk4 `HAVE_EGL` 一致）。
- ❌ 删除公共头文件声明或破坏 ABI（deprecated API 保留签名，仅实现降级）。

## 验证
```bash
# libadwaita-1 1.9.2（本条目产生库，R01 实测通过）
conan create archives/l/libadwaita-1/1.9.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# => meson configure 通过（-Dappstream=disabled），5 个补丁应用，build() 成功
# => test_package 1/1 OK（HARMONY_LIBADWAITA_TEST_PASS，3 个版本 API 断言）
# => conan-verify G1-G5 全 PASS；finish W3 本地 CI 模拟通过
```
对应 .kv `verification_cmd`：`conan create archives/l/libadwaita-1/1.9.2
-pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`。

## 关联条目
- 类似: gtk4/4.22.4 `patches/0001-gdk-gdkdmabuf.c.patch`（HAVE_EGL 守卫先例，
  同解法但不同依赖）
- 相关: E463 / E471 / E527（OHOS 无显示/生态组件缺失的显示-后端类条目，
  触发域相近但机制不同，本条为“依赖可选化”而非“显示后端”）