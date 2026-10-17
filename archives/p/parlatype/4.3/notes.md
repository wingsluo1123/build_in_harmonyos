# parlatype 4.3 适配笔记

## 编译环境
- 构建系统: meson（+ ninja）
- 编译日期: 2026-10-15
- 编译器: clang/clang++（OHOS aarch64，`--target=aarch64-linux-ohos`）
- 状态: built

## 编译步骤

上游用 meson + ninja，交叉编译通过 conan 生成的 toolchain + cross file 完成，不做
`./configure`；配方里用 `meson setup` / `meson compile` / `meson install` 三步。

```bash
# 1) 交叉环境由 conan 提供（profile: ohos-aarch64, compiler=clang 15, compiler.cppstd=17）
meson setup build \
    --cross-file <build_folder>/ohos-aarch64-cross.ini \
    --prefix / \
    -Dhelp=false          # 关闭 yelp 帮助页（见「遇到的问题」#1）

# 2) 编译 + 安装到 conan 的 package 目录（staging）
meson compile -C build
DESTDIR=<pkg_folder> meson install -C build --no-rebuild
```

配方侧要点（`conanfile.py`）：

| 环节 | 处理 |
|------|------|
| `_prepare_host_tool_bins` | 构建期 host 工具（glib-compile-schemas / gtk4-update-icon-cache / gdk-pixbuf-query-loaders 等）重签名 + wrapper，按工具隔离 `libintl` |
| `_normalize_glib_pc` | 修正生成的 `glib-2.0.pc`，去掉多余的 `-lffi` |
| `.pc` 别名 | 为 `gstreamer-1.0` / `gstreamer-app-1.0` / `gstreamer-audio-1.0` 补别名 `.pc`，解决 pkg-config 名称不匹配 |
| `_run_upstream_tests` | 读 `meson-info/intro-tests.json`，按用例驱动测试二进制；无法运行的用例计数并记原因 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `help/meson.build` 调 `gnome.yelp()` → `Program 'itstool' not found` / `code=126` | OHOS 侧 itstool 是 python 脚本，shebang 解释器与 python `libxml2` 绑定在构建环境均缺失 | 加补丁 `0001-meson.build.patch` + `0002-meson_options.txt.patch`：新增 meson 选项 `help`（默认 false），用 `if get_option('help')` 守卫 `subdir('help')`（同 ghex 46.0 先例） |
| 2 | configure 期 `Error relocating .../libgettextsrc-0.22.5.so: libintl_gettext: symbol not found`（exit 127） | 构建期 host 工具加载的 glib `libintl.so.8` 导出 `g_libintl_*`，gettext 的 `libintl.so.8` 导出 `libintl_*`，同名库二选一，不可共存 | `_prepare_host_tool_bins` 按工具做 wrapper 隔离（每个 host 工具用自己的 `LD_LIBRARY_PATH`），不做全局顺序调整 |
| 3 | 链接期 `-lffi` 找不到 | 生成的 `glib-2.0.pc` 里带了冗余 `-lffi`，OHOS 侧无独立 libffi.pc/动态库暴露 | `_normalize_glib_pc` 规范化 `.pc`，剥离冗余 `-lffi` |
| 4 | pkg-config 找不到 `gstreamer-app-1.0` / `gstreamer-audio-1.0` | OHOS gstreamer 包提供的 `.pc` 名称与上游 meson 期望不一致 | 为 `gstreamer-1.0`/`gstreamer-app-1.0`/`gstreamer-audio-1.0` 生成别名 `.pc` |
| 5 | `gnome.post_install()` / icon cache 步骤 EPERM | `gtk4-update-icon-cache`、`glib-compile-schemas` 在构建环境权限受限 | 在 host 工具准备阶段重签名 + 重新编排 PATH，`gtk4-update-icon-cache` 失败不阻塞（记警告） |
| 6 | ITS/msgfmt 阶段 `GETTEXTDATADIR` 缺失导致翻译合并失败 | 构建期 gettext 工具需要显式数据目录 | `build()` 顶部重新应用 wrapper 环境并显式导出 `GETTEXTDATADIR` |
| 7 | appstream/1.2.0 阻塞 | `~/.conan2/global.conf` 里残留的临时预下载配置指向失效缓存 | 还原 `global.conf` 临时配置（用后还原），改用 conan 原生 `download_cache` |

## 源码修改

两个补丁，均为「可移植性」类，不引入平台宏（R8）：

| 补丁 | 变更 | 内容 |
|------|------|------|
| `patches/0001-meson.build.patch` | +3 / -1 | 用 `if get_option('help')` 守卫 `subdir('help')`，使帮助页默认不进构建 |
| `patches/0002-meson_options.txt.patch` | +6 / -0 | 新增布尔选项 `help`（`value: false`） |

## 依赖版本

构建期依赖（conan `requires`）：

| 包 | 版本 | 说明 |
|----|------|------|
| gtk4 | 4.22.4 | GTK4（注意：制品仓里是 `gtk4`，不是 `gtk`） |
| glib | 2.84.0.1.1 | `shared=True`，其他包统一 override 到该版本 |
| libadwaita | 1.8.8 | 与 gtk4/4.22.4 配对（ghex 46.0 先例） |
| gstreamer | 1.28.3 | 音频播放后端 |
| gst-plugins-base | 1.28.3 | 播放所需 base 插件 |
| iso-codes | 4.20.1 | 语言/地区代码 |
| pango | 1.56.4 | override |
| zlib | 1.3.1.1 | override |
| fontconfig | 2.18.1.1 | override |
| fribidi | 1.0.16 | override |

构建期工具（`tool_requires`，R33/W0b：不外借宿主工具）：

| 包 | 版本 |
|----|------|
| gettext | 0.22.5.1 |
| itstool | 2.0.7 |

## 上游测试三步法（R51）

**第一步 清点**：上游测试注册在 `libparlatype/tests/meson.build`（注意不是顶层 `tests/`），
由 `tests` 列表 + `foreach` 逐项 `test()` 注册，共 **7 个用例**：

| # | 用例（源文件） | 类型 | 依赖 |
|---|----------------|------|------|
| 1 | config（`config.c`） | 可运行 | `libparlatype_dep`，`asr_config_data` |
| 2 | player（`player.c`） | 可运行 | `libparlatype_dep` |
| 3 | waveloader（`waveloader.c`） | 可运行 | `libparlatype_dep`，测试数据 `data/test1.ogg` |
| 4 | waveviewer（`waveviewer.c`） | 可运行 | `libparlatype_dep` |
| 5 | gst（`gst.c`） | 内部/静态 | `libparlatype_static_dep` |
| 6 | mediainfo（`mediainfo.c`） | 内部/静态 | `libparlatype_static_dep` |
| 7 | waveloader-static（`waveloader-static.c`） | 内部/静态 | `libparlatype_static_dep` |

每个用例 args 为 `['--tap', '-k']`，env 为 `G_TEST_SRCDIR` / `G_TEST_BUILDDIR` / `LANGUAGE=C`。

**第二步 运行**：在 conan create 的构建环境（OHOS aarch64 交叉构建目录）内驱动测试二进制
逐个执行，结果 **2 run, 2 passed, 0 failed, 5 skipped**。

**第三步 如实回填**：实测 **2 run, 2 passed, 0 failed, 5 skipped**。

> 逐例归属以构建日志中配方打印的 `skip test <name>: <reason>` 行与
> `conanfile.py` 的 `_TEST_SKIP` 为准（本节、`_TEST_SKIP`、`test_package/MANIFEST.yml`
> 三处口径逐字一致）。

**运行通过的 2 个用例**（实测退出码 0，TAP 全绿）：

| 通过的用例 | 证据 |
|-----------|------|
| mediainfo | 本地实测跑通（无需显示器、不加载运行期 GStreamer 插件）；配方未登记跳过，失败即 raise |
| waveloader-static | 同上（静态库变体，实测跑通） |

**跳过的 5 个用例**（逐项技术原因，取自实测日志）：

| 跳过的用例 | 具体技术原因（实测打印） |
|-----------|--------------|
| config | 需要 GTK 显示：`DISPLAY=` 与 `WAYLAND_DISPLAY=` 皆为空，构建环境无 Xvfb/weston → `needs X11/Wayland display` |
| waveviewer | 同上 → `needs X11/Wayland display` |
| gst | OHOS gstreamer 包只提供静态插件库（`libgstcoreelements.a` / `libgstbase-1.0.a` / `libgstcheck-1.0.a` / `libgstcontroller-1.0.a` / `libgstnet-1.0.a`），`<pkg>/lib/gstreamer-1.0/` 下没有共享插件 `.so`，也无 `gst-plugin-scanner` 与插件 registry → `needs shared GStreamer plugins (OHOS ships static .a only)` |
| player | 同上（播放器管线需运行期加载 coreelements） |
| waveloader | 同上（动态库变体需运行期 GStreamer 后端解码 `data/test1.ogg`） |

> 说明：「没有显示环境 / 没有共享插件目录」属于 OHOS 制品仓当前投放形态的客观限制，
> 非配方缺陷；跳过项由 `_TEST_SKIP` 显式登记并逐条打印原因（构建日志
> `skip test <name>: <reason>`），未做静默跳过，其余用例失败即 raise。
> 因此「运行通过」的结论建立在 2 例实跑之上，5 例为显式登记的客观不可用。

## 验证结果

```bash
# W3 本地 CI 全流程（干净无缓存环境）
$ conan create archives/p/parlatype/4.3 --profile:build=... --profile:host=... 
# → RC=0，.ci-result.json exit_code=0

# test_package 静态校验（bin/parlatype 无法在构建机执行 → 走 .symtab 校验）
$ bash archives/p/parlatype/4.3/test_package/test_parlatype.sh
# → 10/10 PASS（含 GStreamer 静态链入证明：gst_* 符号存在于 .symtab）
```

上游测试实测：**2 run, 2 passed, 0 failed, 5 skipped**（7 个用例清点完整，跳过原因见上表）。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/parlatype` | 主程序（GUI 转录编辑器） |
| `lib/libparlatype.so` | 转录引擎共享库 |
| `commands.json`（软件级） | R38：命令行工具声明（hicmd 格式） |
| `test_package/test_parlatype.sh` | 静态校验脚本（10 项断言） |
| `knowledge-extension/` | 知识库扩展四件套（检测脚本/处理策略/文档/复现脚本） |

## 注意事项

- `bin/parlatype` 在构建机（x86_64 Linux）无法执行（OHOS aarch64 ELF），test_package 采用
  `.symtab` 静态校验而非 `--version` 运行；GStreamer 静态链入通过 `gst_` 符号证明，
  **不能用 `readelf -d` 的 DT_NEEDED 判断**（静态链入不产生 DT_NEEDED）。
- 本次适配阻塞点（itstool/yelp 帮助页）已抽成共性知识扩展，见 `knowledge-extension/README.md`。

## R40 深度适配说明（图形 / 多媒体类）

parlatype 落在 R40 明列的**图形渲染（GTK4/libadwaita）与多媒体（GStreamer）**领域，故额外声明：

- **已落实的实质平台适配**（非 stub / 非 `return 0`）：
  1. host 工具链重建：对 glib / gdk-pixbuf / gtk4 / gettext 的构建期可执行文件重新去除
     `.codesign` 段并重签名，并按**工具逐个**隔离 `LD_LIBRARY_PATH`，解决 glib 自带
     `libintl.so.8`（导出 `g_libintl_*`）与 gettext `libintl.so.8`（导出 `libintl_*`）
     同名不同符号集的互斥冲突；
  2. `glib-2.0.pc` 归一化（剔除多余 `-lffi`）+ `gstreamer-1.0` / `gstreamer-app-1.0` /
     `gstreamer-audio-1.0` 的 `.pc` 别名补齐；
  3. GStreamer 静态插件链入（OHOS 制品仓只投放 `.a` 插件，无 scanner/registry）。
- **需人工确认的边界**：构建机无显示服务器（`DISPLAY=`/`WAYLAND_DISPLAY=` 皆空）且
  OHOS 侧只有静态 GStreamer 插件，故**运行期**渲染通路与音频管线（`player`/`gst`/
  `waveloader` 三例）在本环境无法端到端验证；`test_package` 走 `.symtab` 静态校验，
  能证明"音频引擎确实链入二进制"，但**不能替代运行期验证**。请评审在真机（带显示 +
  完整插件）侧确认 GUI 与音频通路。
- 被关闭的仅为 **yelp 帮助页文档目标**（`help` option 默认 false）与上述运行期用例，
  **不涉及任何功能代码删改**。
---

**编译结束**: 2026-10-16 09:25
**最终状态**: built
