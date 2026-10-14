# vlc 3.0.23 适配笔记（OHOS aarch64）

> 2026-09-25 · 2404_87638649 · 任务 vlc 3.0.23（平台任务 id=11723）

## 结论

**conan create 全绿**：libvlc/libvlccore + 283 插件 + vlc 二进制完整产出，
test_package（libvlc_new/version/release API）5/5 PASS。本机构建耗时约 9.5 分钟
（HMDFS 上 283 插件逐个 relink 是 install 阶段耗时主体）。

## 源码与裁剪

- 官方 tarball：https://get.videolan.org/vlc/3.0.23/vlc-3.0.23.tar.xz
  （sha256 e891cae6aa3ccda69bf94173d5105cbc55c7a7d9b1d21b9b21666e69eff3e7e0）
- autotools 构建，交叉 `--host=aarch64-linux-ohos`
- 裁剪：XCB/Wayland/X11/Qt/skins2/notify/ncurses/SDL/VDPAU/VAAPI/V4L2/DVB/
  decklink/macosx/wasapi/oss/alsa/pulse/jack/a52/lua/gnutls/gcrypt/classic-GL 全禁
- codec 全保留：ffmpeg(avcodec/avformat/swscale)+mad+ogg/vorbis/theora/flac/opus+
  dav1d/vpx/x264/x265+dvdnav+libass 字幕链

## 四个补丁（全部在干净 tarball 验证 patch -p1 可应用）

1. **0001 ohos-triplet**：config.guess 加 HarmonyOS case（注意补丁脚本生成的
   `GUESS=` 变量块无效，须 `echo ... ; exit ;;`）；config.sub 四处白名单
   （maybe_os 列表 + ohos-linux 分支 + OS 白名单 + kernel-os 验证列表）
2. **0002 capability-macros**（posix_close + pthread_cancel 合并）：configure.ac
   的 linux 分支 AC_CHECK_FUNCS 追加 posix_close/pthread_cancel/
   pthread_setcancelstate/pthread_testcancel 四函数链接探测——OHOS musl 头文件
   定义了 POSIX_CLOSE_RESTART/PTHREAD_CANCEL_* 宏但未实现函数（头/实现不同步），
   链接探测按符号存在性决定；源码侧 vlc_close/vlc_cancel/vlc_savecancel/
   vlc_restorecancel/vlc_testcancel 依据 HAVE_POSIX_CLOSE/HAVE_PTHREAD_CANCEL
   等 autoconf 能力宏分支，缺能力时走 POSIX 兼容 fallback（close(fd)/no-op）。
   R8 合规：不引入 __OHOS__ 平台宏，glibc/musl 主线等有能力平台行为不变
   （libvlc_new/release 实测正常——vlc 线程退出走 join 不依赖 cancel）
4. **0004 disable-classic-gl**：configure.ac AS_IF 守卫 + 预生成 configure 的
   两处 fallback 编译分支加 `host_os=linux-ohos` 短路（tarball configure 是
   autoconf 2.69 产物，autoconf 2.72 重生成 diff 巨大不可入补丁——**必须双文件
   patch**，只改 configure.ac 的话 CI 无 autoconf 场景下预生成 configure 仍是旧逻辑）

## conan 配方要点（踩坑记录）

- **PkgConfigDeps 生成 pc 的版本字段用包版本**（ffmpeg/4.4.8），vlc 要求
  libavcodec>=57.37.100（库 ABI 版本号）→ build() 里用包内原生 pc
  （lib/pkgconfig/libavcodec.pc，Version: 58.134.100）替换并**逐行重写路径**
  （原生 pc 的路径变量可能是构建期残留 b/<hash>/p——不要用字符串 replace 猜，
  逐行 prefix=/exec_prefix=/libdir=/includedir= 全部重写为 conan 包路径）
- **x264 同理**（conan pc Version: r3223，vlc 要求 >=0.148；原生 0.165.3223）
- **libogg 版本碎片**：flac(1.3.5)/libvorbis(1.3.6)/libtheora(1.3.6.2) 三方
  requires 互相冲突 → 顶层 `self.requires("libogg/1.3.6", force=True)`（另
  libopus/libvpx 与 ffmpeg 传递链冲突同理 force）
- **静态库传递依赖**：flac/vorbis 的 `Requires.private: ogg` 不被 pkg-config
  默认展开 → 提升公共 Requires；x265 静态库 Libs 补 -lc++
- **vlc 3.0 上游 bug**：fontconfig.c 只注入 -DHAVE_FONTCONFIG 不注入
  FONTCONFIG_CFLAGS（4.0 修复）→ freetype2.pc 的 Cflags 并入 fontconfig include
- **fribidi 头在 include/fribidi/ 子目录**，vlc `#include <fribidi.h>` 直引 →
  fribidi.pc Cflags 补子目录路径
- **opus 头在 include/opus/**，vlc `#include <opus.h>` 直引 → opus.pc
  includedir 改指 include/opus
- **libmad 检测不走 pkg-config**：configure 用 `--with-mad=PATH` +
  AC_CHECK_HEADERS/AC_CHECK_LIB → requirements 里取 package_folder 显式传
- **BUILDCC**：构建期工具（fourcc_gen）本机执行。本机即 aarch64 HarmonyOS，
  clang 默认 target 即本机 → `Environment().define("BUILDCC", CC)` 注入
  （Autotools.configure() 不支持 vars= 参数）
- **HMDFS umask 077（E011）**：configure/config.status 内嵌 umask 077 的
  mktemp -d 目录对构建进程不可写 → build() 里 `replace_in_file` sed 成 022
- **补丁后 automake 重建链**：0004 改 configure.ac → 比 aclocal.m4 新 →
  CI 触发 aclocal-1.16（不存在 + @am_AUTOM4TE@ 未替换 → 127）。修法：build()
  里按依赖序 touch 时间链（m4/*.m4+configure.ac 最旧 < aclocal.m4 < configure <
  Makefile.in 最新）。**注意 os.utime 逐文件调用纳秒级递增**——必须按依赖顺序
  循环且时间值显式递增（`_touch_seq(t += 0.001)`），同刻乱序 touch 仍触发重建
- **test_package 的 cmake 启动**：PATH 上的 cmake 是 OHOS aarch64 ELF
  （NEEDED libc++_shared.so，在 /system/lib64），conan build env 替换式
  LD_LIBRARY_PATH 丢失系统路径 → rc=127。修法：Environment prepend
  /system/lib64:/system/lib64/platformsdk:/system/lib64/chipset-pub-sdk
- **test_vlc 运行环境**：conan 的 cmake.test()（ctest）进程不含 conanrun 的
  LD_LIBRARY_PATH → test 二进制加载 libvlc.so.5 失败。self.run(env=list) 在
  OHOS loader 上不生效 → 用 `Environment().vars().apply()` 上下文 + VLC_PLUGIN_PATH
  指向包内 lib/vlc/plugins（libvlc_new 需插件树，否则报 stale plugins cache
  ——首次还需删 plugins.dat）

## 上游测试（N=22 实测）

vlc 3.0.23 的 test/Makefile.am 注册 `TESTS = $(check_PROGRAMS) check_POTFILES.sh`
（**不是**"无标准 make check"——比任务描述乐观，有完整 automake 套件）：
- 20 个无条件 check_PROGRAMS + test_modules_tls（ENABLE_SOUT 条件）+ check_POTFILES.sh = N 22
- 本机交叉构建 `make check` 实测：**PASS 17 / FAIL 4 / SKIP 1**
- 失败 4 项全部平台限制可定性：
  - test_src_input_stream / test_modules_keystore：硬编码 /tmp（OHOS 只读，E002）
  - test_libvlc_media：fd:// 目录枚举 subitem 超 alarm(10s)（HMDFS 慢，SIGALRM 142）
  - check_POTFILES.sh：校验 Qt 头存在性（--disable-qt 裁剪后必然缺失）
- SKIP 1：test_modules_tls（TLS 插件裁剪，上游 exit 77 语义）

## 依赖版本选型（制品仓实测可用）

ffmpeg/4.4.8（非任务描述的 2.8.9/4.4.6——仓内实际 4.4.8/5.1.10/6.1.6/7.1.5/8.0.3/8.1.2，
选 4.4.8 是 vlc 3.0.x 时代的稳定线）+ libmad/0.15.1b + dav1d/1.5.0 +
libogg/1.3.6（force 统一）+ libvorbis/1.3.7 + libtheora/1.2.0-alpha1 +
flac/1.5.0 + libopus/1.6.1 + libvpx/1.16.0 + x264/r3223 + x265/4.2 +
libdvdnav/7.0.0 + fribidi/1.0.16 + libass/0.17.5（字幕链 freetype/fontconfig/
harfbuzz 由 libass 传递）。

## 产物

- lib/libvlc.so.5.6.1 + lib/libvlccore.so.9.0.1（核心库）
- lib/vlc/plugins/ 下 25 类 283 个 *_plugin.so
- bin/vlc（命令行播放器入口，shell wrapper）
- include/vlc/ 完整公共头树

test_package：libvlc_get_version（3.0 前缀校验）+ libvlc_get_compiler +
libvlc_new(0,NULL)/libvlc_release 实例生命周期——5/5 PASS。
---

**编译结束**: 2026-09-25 12:21
**最终状态**: built

## vlc-gui 变体增量（相对 vlc 3.0.23 基件）

### 依赖增量
- qt5-qtbase/5.15.2.2（force 收敛：qt5-qtsvg/5.15.2.1 要求 5.15.2，收敛到模块面已验证的 5.15.2.2——同 5.15 系列 Qt5 库 soname 不变 ABI 兼容）
- qt5-qtsvg/5.15.2.1（vlc configure.ac L3866 PKG_CHECK_MODULES(QT, [Qt5Core Qt5Widgets Qt5Gui **Qt5Svg**]) 必需——qtbase 不含 Svg 模块，缺此 PKG_CHECK 失败静默落入 qmake6 fallback→Qt 被禁）
- zlib/1.3.1.1 force（qt5-qtbase 传 1.3.1，ffmpeg 链用 1.3.1.1）
- expat/2.8.2.1 force（dbus/1.14.10 传 2.8.2，fontconfig 链用 2.8.2.1）

### configure 增量
- 删 --disable-qt（基件裁剪矩阵中唯一改动；Qt auto-detect 启用）

### Qt 探测三通道（顺序敏感，create5→create12 五轮实证）
1. **PKG_CONFIG_PATH 进程直注**：qt5-qtbase/qt5-qtsvg 包本体 lib/ 内原始 .pc（Qt5Core.pc/Qt5Svg.pc 命名正确）——buildenv_info 注入不达 autotools 子 shell（create8 config.log 实证 No package 'Qt5Core' found），必须 os.environ 直注。
2. **显式 qtsvg flags**：CXXFLAGS/LDFLAGS 注入 qtsvg 的 include/lib（configure 烘进 Makefile 的确定性兜底——create11 实证 configure 探测过了但 QtSvg 的 -I 未进 views.cpp 编译行）。
3. **QT_CFLAGS/QT_LIBS 预设**：autoconf PKG_CHECK_MODULES 尊重预设环境变量跳过自身探测（在 PKG_CONFIG_PATH 就位后用 pkg-config 算出再写死）。
- 另：qt5-qtbase/bin（moc/rcc/uic/qmake）注入 PATH（AC_PATH_PROGS 探测）+ LD_LIBRARY_PATH=/system/lib64（host 工具是 arm64 ELF 链系统 libc++_shared.so）。

### package_info 增量
- 删 cmake_file_name="vlc"：GUI 变体按包名 vlc-gui 生成 vlc-guiConfig.cmake（沿用基件的 "vlc" 会导致 find_package(vlc-gui) 找不到配置文件——create4 实证）。

### test_package 增量
- CMakeLists：vlc::vlc → vlc-gui::vlc-gui；find_package(vlc) → find_package(vlc-gui)。
- 新增 Qt GUI 插件成色断言：lib/vlc/plugins/gui/*_plugin.so 必须在包内（gui 变体区别于基件的核心证明）。

### 成色实证（create12）
- libqt_plugin.so 3840576 bytes 在 lib/vlc/plugins/gui/
- readelf -d NEEDED：libQt5Widgets.so.5 / libQt5Svg.so.5 / libQt5Gui.so.5 / libQt5Core.so.5 / libc++_shared.so / libc.so / libvlccore.so.9
- test_package ALL TESTS PASSED（libvlc API 4 断言 + gui 插件断言）

### 踩坑补录
| # | 症状 | 根因 | 处置 |
|---|------|------|------|
| V1 | Version conflict zlib/1.3.1 vs 1.3.1.1 | qt5-qtbase 传递版本碎片 | force 收敛 zlib/1.3.1.1 |
| V2 | Version conflict expat/2.8.2 vs 2.8.2.1 | dbus 传递版本碎片 | force 收敛 expat/2.8.2.1 |
| V3 | find_package(vlc-gui) 找不到配置 | 基件 cmake_file_name="vlc" 被复制 | 删该属性，包名自然生效 |
| V4 | target vlc::vlc not found | test_package CMakeLists 复制未改 | vlc-gui::vlc-gui |
| V5 | qmake6: command not found → Qt 被禁 | PKG_CHECK(QT) 需 Qt5Svg（qtbase 无），失败静默落 qmake6 fallback | 补 qt5-qtsvg 依赖 |
| V6 | No package 'Qt5Core' found（config.log） | buildenv_info 不达子 shell | PKG_CONFIG_PATH os.environ 直注 |
| V7 | QSvgRenderer file not found | configure 探测过了但 QtSvg -I 未进编译行 | CXXFLAGS 显式注入 + QT_CFLAGS 预设 |
| V8 | ConanOutput has no attribute 'warn' | conan 2.29 API 名 | self.output.warning |
| V9 | Version conflict qt5-qtbase/5.15.2 vs 5.15.2.2 | qt5-qtsvg 传递 5.15.2 | force 收敛 5.15.2.2 |
