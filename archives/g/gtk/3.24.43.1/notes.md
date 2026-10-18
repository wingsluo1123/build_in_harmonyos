# gtk 3.24.43.1 适配笔记（X11 后端变体）

## 为什么有这个版本（R37：同上游版本 + 适配变更 → 递增版本号后缀）

- 已发布的 `gtk/3.24.43` 是 **broadway-only** 构建：
  `gdkconfig.h` 中 `#undef GDK_WINDOWING_X11`、不安装 `gtk+-x11-3.0.pc`，
  `libgtk-3.so` 内 `gdk_x11_*` 符号为 0。
- 后果：X11-only 消费者直接编译失败。实测案例 **vino 3.22.0**：
  `server/smclient/eggsgmclient.c:348` 的私有头用 `GDK_WINDOWING_X11`
  守卫声明，OHOS 版 gtk 无该宏 → 声明缺失 → 编译报错；
  vino `configure` 还要求 `gtk+-x11-3.0`（`configure.ac:285`）pkg-config 条目。
- 本版本与 3.24.43 **同源同版本**，仅适配层变更（启用 X11 后端 + X11 依赖），
  按 R37 递增版本号后缀（cnb.cool 不支持同版本多 recipe revision 并存）。

## 与 3.24.43 的差异

| 项 | 3.24.43 | 3.24.43.1 |
|----|---------|-----------|
| meson 选项 | `-Dx11_backend=false` | `-Dx11_backend=true`（broadway 保留） |
| X11 依赖 | 无 | xorgproto/libx11/libxext/libxrender/libxi/libxrandr/libxcursor/libxfixes/libxcomposite/libxdamage |
| 产物 | `gtk+-3.0.pc` | `gtk+-3.0.pc` + **`gtk+-x11-3.0.pc`** |
| test_package | 版本/类型 API | 追加 X11 实质断言（见下） |

其余（meson 构建、glib 工具 wrapper、.so 签名、gresources pixdata 剥离、
fribidi/gmodule .pc 修补）与 3.24.43 完全一致，未改动。

## X11 依赖版本选择

均取 ohpcd 制品仓已发布的最新 recipe 版本（W0 预检）：

- xorgproto/2025.1、libx11/6.4.0、libxext/6.4.0、libxrender/0.9.12、
  libxi/6.1.0、libxrandr/1.5.5.1、libxcursor/1.2.3.1、libxfixes/6.1.0、
  libxcomposite/0.4.6、libxdamage/1.1.6.1
- libx11 与 libxext 必须同谱系：libxrender/0.9.12 pin libx11/1.8.13，
  而 libxext/6.4.0 依赖 libx11/6.4.0，混用触发版本冲突 →
  顶层 override `libx11/6.4.0` 并取 libxext/6.4.0（6.4.0.1 依赖另一谱系）。
- 上游 `meson.build` 的 x11 分支（gtk+-3.24.43/meson.build:556-565）要求
  x11/xext/xrender/xi/xrandr 必需，xcursor/xdamage/xfixes/xcomposite 标 optional，
  本配方显式提供后者，保证 X11 类上层软件拿到的 gdk 具备完整 X11 能力。
- `xinerama=no` 保持不变；`libxkbcommon` 仅在 wayland 后端需要
  （meson.build:441 `required: wayland_enabled`），X11 后端不需要，未引入。

## 依赖链修复（X11 后端带出的传递依赖）

- **atk-bridge-2.0**：gtk x11 分支硬性依赖（`meson.build:568`，version
  at_spi2_atk_req），由 at-spi2-core 的 bridge 组件提供。制品仓
  at-spi2-core/2.60.5 走 glib2/2.88.0 谱系（与本图 glib 谱系及 zlib
  1.3.1/1.3.1.1 冲突）→ 产出 **at-spi2-core/2.60.5.1**（同源同版本，
  仅切依赖谱系至 glib 谱系，R37 后缀；本地 conan create 全绿）。
- **glib/2.84.0.2**：glib 谱系 2.84.0.1 的 proxy-libintl subproject 装成独立
  `libintl.so`，而 atk/atspi（经 glib/gi18n*.h 使用 `<libintl.h>`）在静态库
  链接期报 `undefined symbol: libintl_dgettext` / 缺 `g_libintl_*`。2.84.0.2
  将该 subproject 改为 static 链接，代理实现并入 `libglib-2.0.so`（实测
  `nm -D`：9 个 g_libintl_* 定义、无 libintl.so NEEDED）→ 消费者 `-lglib-2.0`
  即解析，无需 gettext 包（曾试 gettext 真实 libintl 方案，因与 glib 自身
  运行时引用冲突而放弃）。
- **expat/2.8.2.1**：at-spi2-core → dbus/1.14.10 钉 expat/2.8.2，本图其余
  依赖（fontconfig/libxml2 等）用 expat/2.8.2.1 → 顶层 override 统一
  （patch 级 ABI 兼容）。
- 顶层 override 汇总：`glib/2.84.0.2`、`expat/2.8.2.1`、`cairo/1.18.4.1`
  （pango 原钉 1.18.4）、`libx11/6.4.0`。

## 测试完备性（R34 + R51）

- **test_package（消费者用例）**：
  1. 编译期：`#ifndef GDK_WINDOWING_X11 → #error`（后端缺失直接编译失败）；
  2. 链接期：调用 `gdk_x11_display_get_type()`（该符号仅 X11 后端编入 libgdk-3）；
  3. pkg-config 契约：CMake 断言 `gtk+-x11-3.0`（vino 一类消费者的探测入口）不可缺；
  4. 原有 `gtk_get_major_version` / `gtk_check_version(3,24,43)` / `gtk_widget_get_type`。
- **上游测试**：真实执行。gtk 上游 tests/ 需显示会话，OHOS 无 X11，因此用
  构建产物 `gdk/broadway/broadwayd` 起无头 display（`GDK_BACKEND=broadway`），
  由 `build()` 内 `_run_upstream_tests()` 跑 `meson test`。实测 194 项全部执行，
  结果分三类：
  1. 通过 58 项（非 reftest 套件主体用例）；
  2. reftest 127 项：参考 PNG 由上游桌面环境（x11 + fontconfig 字体 +
     Adwaita 主题）生成，broadway 无头后端栅格化结果不一致，像素比对通过数
     随 worker 渲染条件剧烈摆动（真机 x11 108/127、CI-006 12/127、
     CI-017 0/127），不具判别力，因此**不作回归判据**；只断言整套 127 项
     确实执行过（执行数下限 122），通过/不一致项数如实记账进日志；
  3. 已知环境限制 9 项（`displayclose` broadway 无 display manager 会话、
     `window`/a11y 若干时序敏感用例等），均已在配方 `_TESTS_ENV_LIMITED`
     中附技术原因注释。
  白名单外失败会触发整套 `-j1` 串行重跑一次判定抖动，确定性缺陷照样拦截。

## 编译命令

```bash
cd archives/g/gtk/3.24.43.1
conan create . --build=missing \
  -pr:h ci/conan/profiles/ohos-aarch64 -pr:b default
```

## 编译结果（2026-10-04，aarch64-unknown-linux-ohos）

- 构建：`PROGRESS=[952/952] ERR=0`（meson，`x11_backend=true` + `broadway_backend=true`）。
- 产物：`libgtk-3.so`、`libgdk-3.so`，pkg-config 条目
  **`gtk+-x11-3.0.pc`** + `gtk+-3.0.pc` + `gdk-x11-3.0.pc`。
- 验收点全部满足：
  1. `gtk+-x11-3.0.pc` 存在 ✓
  2. `gdk_x11_display_get_type` 符号存在（X11 后端已编入 libgdk-3）✓
  3. test_package 全绿 ✓（`test GTK 3.24.43.1 (X11 backend): OK`，ctest 1/1 Passed）
- test_package 覆盖：版本/类型 API（`gtk_get_major_version` /
  `gtk_check_version(3,24,43)` / `gtk_widget_get_type`）、`GDK_WINDOWING_X11`
  编译期断言、`gdk_x11_display_get_type` 链接期断言、
  `gtk+-x11-3.0` pkg-config 契约断言。
- 上游测试：真实执行（broadway 无头 display + `meson test`），194 项全跑，
  通过 58 项；reftest 127 项虽全部执行，但参考 PNG 采自桌面渲染环境，无头
  后端下像素比对通过数在 0–12 间摆动、不具判别力，故不作回归判据（仅校验
  执行数）；另有 9 项已附原因的环境限制用例。详见上文「测试完备性」。

## 关联

- 消费者：`archives/v/vino/3.22.0`（本版本即为解除其
  `eggsgmclient.c:348` 阻塞而产出，PR 前缀【依赖项】）。
- 上游源：download.gnome.org（R39，主源 + 华为云镜像 fallback），sha256 与
  3.24.43 相同（同一 tarball）。
