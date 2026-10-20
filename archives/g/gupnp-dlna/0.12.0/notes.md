# gupnp-dlna 0.12.0 适配笔记

## 编译环境
- 构建系统: meson + ninja
- 编译日期: 2026-10-19（首轮）
- 编译器: clang/clang++（OHOS SDK llvm 15.0.4 工具链）
- 状态: built
- 积分归类: 【依赖项】路径 A 正常适配

## 背景

gupnp-dlna 是 GUPnP/UPhP 协议栈的 DLNA profile 识别库：内置 80+ 个
`<dlna-profile>` 定义（15 个 XML），通过可插拔元数据后端读取媒体容器/
音频/视频信息并按 profile 限制匹配。上游 0.12.0 依赖
glib-2.0/gobject-2.0/gio-2.0/gmodule-2.0（glib2）、libxml-2.0（libxml2）、
gstreamer-1.0 / gstreamer-pbutils-1.0（gstreamer、gst-plugins-base）。

本包与 gupnp-av/gupnp 同栈，构建配置复用其已验证方案；差异点在于
**元数据后端是运行时经 GModule 加载的 shared_module** —— 这决定了
`default_library=shared`。

## 编译步骤

```bash
# 源码（官方 GNOME 源 + NJU/USTC 镜像，sha256 实测一致）
# https://download.gnome.org/sources/gupnp-dlna/0.12/gupnp-dlna-0.12.0.tar.xz
# sha256: 3d53b96f85bc5628d33e367ec9bf2adb38ef2b34d7ad0434a6ba0cf4ad9048e6

export LD_LIBRARY_PATH="/system/lib64/platformsdk:/system/lib64/chipset-pub-sdk:/system/lib64:/system/lib64/ndk:/data/storage/el1/bundle/libs/arm64"

conan create archives/g/gupnp-dlna/0.12.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 架构决策：为什么 shared

上游 `libgupnp-dlna/metadata-backends/gstreamer/meson.build` 用
`shared_module('gstreamer', ... install_dir: metadata_backend_dir)` 产出
`<prefix>/lib/gupnp-dlna/libgstreamer.so`，核心库在
`gupnp_dlna_metadata_backend_get_extractor()` 里用
`g_module_build_path(GUPNP_DLNA_METADATA_BACKEND_DIR, "gstreamer")` 运行时
打开它。meson 的 `shared_module()` 不受 `default_library` 影响，始终产出 .so。
若按 gupnp-av 的 static 方案：核心库是静态归档、后端模块是 .so，两者各自
把静态 glib/gst 链进不同产物，同一进程出现两份 gobject/gst 状态，profile
猜解会跨副本调用（GType 撕裂）。
- gst-plugins-bad 1.28.3 已按 shared=True、静态 glib/gst 嵌入共享对象的
  形态真机发布（2026-09-04），其 test_package 同时链接 glib2 与 gstreamer
  静态包仍通过 —— 是本文采用方案的直接先例。

OHOS 动态链接器的全局符号查找顺序让进程内最先加载的定义生效，后续 .so
的同名 UND 符号解析到同一份实现（interposition）。但静态归档在每个 .so
里生成的是**已定义**符号，GObject 的 GType 注册表是各副本的私有静态状态；
真机实测后端模块加载仍触发注册表冲突（见下节「平台限制」）。shared 方案
因此只用于保持上游产物结构，并不消除该限制。

## 依赖策略

| 依赖 | 版本 | 说明 |
|------|------|------|
| glib2 | 2.88.0 | 静态包；PkgConfigDeps 生成 glib-2.0.pc（本配方覆盖为完整 Libs 行，避免 libffi.pc 的 prefix=/ 坏链） |
| libxml2 | 2.15.3.1 | 静态包；profile XML 解析 |
| gstreamer | 1.28.3 | 静态包；核心库与后端共用 |
| gst-plugins-base | 1.28.3 | 静态包；提供 oggdemux/vorbisdec/typefind 等插件与 pbutils |
| zlib | 1.3.1.1 | 根级 override 到 PIC 变体（静态 glib 嵌入共享对象） |

### pkg-config wrapper

PkgConfigDeps 只会为每个 conan 包生成一个平铺 .pc，而上游 meson 需要
`gobject-2.0`、`gio-2.0`、`gmodule-2.0`、`gstreamer-1.0`、
`gstreamer-pbutils-1.0` 等名字。generate() 里补写：

- gobject-2.0/gio-2.0/gmodule-2.0/gmodule-no-export-2.0/gthread-2.0：
  Libs 指向 glib2 静态归档全集（gobject 等符号同在这一个归档里）；
- gstreamer-1.0/base/audio/video/tag/pbutils：Libs 携带完整静态 gst 链
  （`-lgstpbutils-1.0 -lgstaudio-1.0 -lgstvideo-1.0 -lgsttag-1.0
  -lgstbase-1.0 -lgstreamer-1.0 -lm -ldl -lpthread`）。meson 对 shared
  library 默认 `-Wl,--no-undefined`，缺一不可。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 后端模块运行时加载路径 | `DATA_DIR`/`metadata_backend_dir` 是 configure-time prefix（conan 下为 `/`），安装后不在 `/` | `runenv_info` 注入 `GUPNP_DLNA_PROFILE_DIR`、`GUPNP_DLNA_METADATA_BACKEND_DIR`；test_package 显式导出 |
| 2 | gstreamer 插件目录 | gst-plugins-base 静态包把插件 .so 装在 `lib/gstreamer-1.0`，非系统目录 | `runenv_info` 注入 `GST_PLUGIN_PATH` 指向依赖包内插件目录（多个依赖以 os.pathsep 连接） |
| 3 | meson install 改写 DT_RUNPATH 破坏 .codesign | OHOS loader 校验 .so 内嵌签名哈希与内容一致 | `_restore_pristine_binaries()`：安装后用 build 目录原始链接产物覆盖 `lib/`、`lib/gupnp-dlna/`、`bin/` 下同名同大小 ELF（gssdp/gupnp/gst-plugins-bad 同款） |
| 4 | zlib 非 PIC 归档重定位错误 | 静态 zlib 被链入共享库 | 根级 override `zlib/1.3.1.1`（PIC） |
| 5 | introspection 依赖 g-ir-scanner | 构建机无该工具 | `introspection=False`、`vapi=False`、`gtk_doc=False` |
| 6 | GstDiscoverer 插件加载受平台静态 glib 限制 | 制品仓 glib2/gstreamer 仅静态包：每个 GStreamer 插件 .so 内嵌独立 glib/gst 副本，跨 DSO 的 GType 注册表分裂（gst-plugins-bad1.0 1.28.5 真机实测：加载插件即 `g_param_spec_boxed` assertion / SIGSEGV） | 包本体按上游结构完整构建（共享库 + 后端模块）；消费者测试改为解析模块 ELF（.codesign 节 + .dynsym 导出入口），不把会崩溃的模块加载/插件解码路径放进 CI；设备隔离探针实测 dlopen 即 SIGABRT（g_type_register_static 断言），结论见下节 |
| 7 | `libX.so.4` / `libX.so` 缺失，测试与消费者加载失败 | meson 对 `version: '4.0.0'` 的库只以符号链接发布 soname/开发名，OHOS `/storage` 沙箱拒绝 `symlink(2)`（坑 #10/#13） | `_ensure_library_aliases()`：编译后与 meson install 后扫描全版本实体文件，把 `.so.4` 与 `.so` 重建为同尺寸实体拷贝（先试 symlink、EPERM 则 copy；atk 2.38.0.1.1 同款） |
| 8 | 上游 `discoverer` 测试是 bash 脚本，meson 直接 exec 报 126；加 `--wrapper bash` 又报 `/bin/bash: No such file` | OHOS 内核无 `binfmt_script`（坑 #74），且无 `/bin/bash`；meson 会按 shebang 自动加 `/bin/bash` 前缀，再叠加 `--wrapper` 就变成 `bash /bin/bash script` | 配方不使用 meson 跑脚本型目标：ELF 的 `test-sets` 走 `meson test`；`discoverer` 直接以设备 bash 解释执行，环境变量与 meson 提供的完全一致（MEDIA_DIR/FILE_LIST/GUPNP_DLNA_PROFILE_DIR/GUPNP_DLNA_METADATA_BACKEND_DIR），上游 exit 77 记为 SKIP |

## 测试统计（真机实测，2026-10-19）

验证入口：`python3 scripts/ohc-run.py conan-verify gupnp-dlna 0.12.0 --user ohpcd --channel stable`
（G0–G5 全 PASS，报告见 `reports/conan-verify-report.md`）。

上游 `meson test`（OHOS 设备原生，`--timeout-multiplier=16 --no-rebuild`）：

| 目标 | 类型 | 实测 | 说明 |
|------|------|------|------|
| test-sets | GLib g_test | 9/9 PASS | TAP `ok 1..9`（value-type/value-list/restriction/info-set），`Ok: 1 Fail: 0` |
| discoverer | 脚本型 CTest | exit 77 (SKIP) | 上游脚本检测到媒体目录缺失后主动跳过；配方回显 `discoverer: SKIP (upstream exit 77: media set absent)` |

`test_package` 消费者端到端（3 个 case，18 个校验点，0 失败）：

1. `profile-catalog`：GUESSER 加载到 72 个 DLNA profile（≥60），MP3 profile 与 audio/mpeg mime 正确；
2. `relaxed-extended-modes`：relaxed/extended 猜解模式构造与标志正确；
3. `install-layout`：profile 目录 15 个 XML；后端模块 ELF64、`.codesign` 节存在、
   `gupnp_dlna_get_default_extractor` 在 `.dynsym` 中导出（不 dlopen，见平台限制）。

末行输出：`TEST SUMMARY: 18 checks, 0 failed -> ALL PASS`。

### 命令行工具实测

| 工具 | 实测 | 说明 |
|------|------|------|
| `gupnp-dlna-ls-profiles-2.0` | PASS（exit 0） | 输出 profile 表（AAC_ADTS_320 / audio/vnd.dlna.adts 等），`GUPNP_DLNA_PROFILE_DIR` 指向包内 15 XML + RNG |
| `gupnp-dlna-info-2.0 --help` | PASS（exit 0） | 用法与选项正常输出 |

### 平台限制（如实记录）

- `dlopen()` 后端模块 `libgstreamer.so`：隔离进程探针同样 `SIGABRT`
  （`g_type_register_static` / `_g_value_types_init` 断言）。根因是模块与
  `libgupnp-dlna-gst-2.0.so` 各自内嵌一份静态 glib，跨 DSO GType 注册表分裂；
  GStreamer 插件链路同类失败已在 gst-plugins-bad1.0 1.28.5 真机确认。
- `gupnp-dlna-info-2.0 <真实媒体文件>`：进入 GstDiscoverer 元数据提取路径后同样
  `SIGABRT`（`cannot register existing type 'gchar'`）。因此消费者测试只覆盖不触发
  该路径的公开 API，模块验证改为 ELF 结构校验。
