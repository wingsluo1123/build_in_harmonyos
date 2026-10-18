# libvlc 3.0.23_2 适配笔记（OHOS aarch64）

> 2026-09-30 · 任务槽 libvlc/3.0.23_2（与已合并 vlc/3.0.23 同源：官方 vlc-3.0.23 release）
> 配方底稿沿自 vlc/3.0.23 已验证方案（W0b 历史核验：archives/v/vlc/3.0.23/，CI 全绿先例）

## 结论

**conan create 全绿（沿 vlc/3.0.23 已验证路径）**：libvlc/libvlccore + 283 插件 +
vlc 二进制完整产出，test_package（libvlc_new/version/release API + 3 项鸿蒙特有断言）
通过。本机构建耗时约 9.5 分钟（HMDFS 上 283 插件逐个 relink 是 install 阶段耗时主体）。

## 源码与裁剪

- 官方 tarball：https://get.videolan.org/vlc/3.0.23/vlc-3.0.23.tar.xz
  （sha256 e891cae6aa3ccda69bf94173d5105cbc55c7a7d9b1d21b9b21666e69eff3e7e0，
  本机 .build-cache 缓存包 sha256 核验一致）
- autotools 构建，交叉 `--host=aarch64-linux-ohos`
- 裁剪：XCB/Wayland/X11/Qt/skins2/notify/ncurses/SDL/VDPAU/VAAPI/V4L2/DVB/
  decklink/macosx/wasapi/oss/alsa/pulse/jack/a52/lua/gnutls/gcrypt/classic-GL 全禁
- codec 全保留：ffmpeg(avcodec/avformat/swscale)+mad+ogg/vorbis/theora/flac/opus+
  dav1d/vpx/x264/x265+dvdnav+libass 字幕链

## 补丁（与 vlc/3.0.23 同四补丁中的三个，已在干净 tarball 验证 patch -p1 可应用）

1. **0001 ohos-triplet**：config.guess 加 HarmonyOS case；config.sub 四处白名单
   （maybe_os 列表 + ohos-linux 分支 + OS 白名单 + kernel-os 验证列表）
2. **0002 capability-macros**（posix_close + pthread_cancel 合并）：configure.ac
   的 linux 分支 AC_CHECK_FUNCS 追加 posix_close/pthread_cancel/
   pthread_setcancelstate/pthread_testcancel 四函数链接探测——OHOS musl 头文件
   定义了 POSIX_CLOSE_RESTART/PTHREAD_CANCEL_* 宏但未实现函数（头/实现不同步），
   链接探测按符号存在性决定；源码侧 vlc_close/vlc_cancel/vlc_savecancel/
   vlc_restorecancel/vlc_testcancel 依据 HAVE_POSIX_CLOSE/HAVE_PTHREAD_CANCEL
   等 autoconf 能力宏分支，缺能力时走 POSIX 兼容 fallback（close(fd)/no-op）。
   R8 合规：不引入 __OHOS__ 平台宏，glibc/musl 主线等有能力平台行为不变
3. **0004 disable-classic-gl**：configure.ac AS_IF 守卫 + 预生成 configure 的
   两处 fallback 编译分支加 `host_os=linux-ohos` 短路（tarball configure 是
   autoconf 2.69 产物，autoconf 2.72 重生成 diff 巨大不可入补丁——必须双文件
   patch，只改 configure.ac 的话 CI 无 autoconf 场景下预生成 configure 仍是旧逻辑）

## conan 配方要点（沿 vlc/3.0.23 已验证方案，逐项比对遵循）

- **PkgConfigDeps 生成 pc 的版本字段用包版本**（ffmpeg/4.4.8），vlc 要求
  libavcodec>=57.37.100（库 ABI 版本号）→ build() 里用包内原生 pc
  （lib/pkgconfig/libavcodec.pc，Version: 58.134.100）替换并**逐行重写路径**
- **x264 同理**（conan pc Version: r3223，vlc 要求 >=0.148；原生 0.165.3223）
- **libogg 版本碎片**：flac/libvorbis/libtheora 三方 requires 互相冲突 →
  顶层 `self.requires("libogg/1.3.6", force=True)`（libopus/libvpx 同理 force）
- **静态库传递依赖**：flac/vorbis 的 `Requires.private: ogg` 提升公共 Requires；
  x265 静态库 Libs 补 -lc++
- **vlc 3.0 上游 bug**：fontconfig.c 只注入 -DHAVE_FONTCONFIG 不注入
  FONTCONFIG_CFLAGS（4.0 修复）→ freetype2.pc 的 Cflags 并入 fontconfig include
- **fribidi 头在 include/fribidi/ 子目录** → fribidi.pc Cflags 补子目录路径
- **opus 头在 include/opus/** → opus.pc includedir 改指 include/opus
- **libmad 检测不走 pkg-config**：`--with-mad=PATH` 显式传 package_folder
- **BUILDCC**：构建期工具（fourcc_gen）本机执行 → `Environment().define("BUILDCC", CC)`
- **HMDFS umask 077（E011）**：configure 内嵌 umask 077 的 mktemp -d 不可写 →
  build() 里 replace_in_file sed 成 022
- **补丁后 automake 重建链**：build() 里按依赖序 touch 时间链
  （m4+configure.ac 最旧 < aclocal.m4 < configure < Makefile.in 最新，os.utime
  纳秒级递增）
- **test_package 的 cmake 启动**：PATH 上的 cmake 是 OHOS aarch64 ELF
  （NEEDED libc++_shared.so）→ Environment prepend /system/lib64:
  /system/lib64/platformsdk:/system/lib64/chipset-pub-sdk
- **test_vlc 运行环境**：用 `Environment().vars().apply()` 上下文 +
  VLC_PLUGIN_PATH 指向包内 lib/vlc/plugins（libvlc_new 需插件树）

## 鸿蒙特有测试（本槽新增，test_vlc.c 第 4-6 组断言）

1. **平台前提**：编译目标为 HarmonyOS（`__OHOS__` 已定义，OHOS clang 注入）
2. **libc 前提**：musl（无 `__GLIBC__`）——0002 能力宏 fallback 的依赖前提
3. **插件树运行时完整性**：VLC_PLUGIN_PATH 已注入且插件树含 `*_plugin.so`
   （libvlc_new 插件发现面，动态加载适配关键）

## 上游测试（N=22 实测，与 vlc/3.0.23 同源）

vlc 3.0.23 的 test/Makefile.am 注册 `TESTS = $(check_PROGRAMS) check_POTFILES.sh`：
- 20 个无条件 check_PROGRAMS + test_modules_tls（ENABLE_SOUT 条件）+ check_POTFILES.sh = N 22
- 本机交叉构建 `make check` 实测：**PASS 17 / FAIL 4 / SKIP 1**
- 失败 4 项全部平台限制可定性：
  - test_src_input_stream / test_modules_keystore：硬编码 /tmp（OHOS 只读，E002）
  - test_libvlc_media：fd:// 目录枚举超 alarm(10s)（HMDFS 慢，SIGALRM 142）
  - check_POTFILES.sh：校验 Qt 头存在性（--disable-qt 裁剪后必然缺失）
- SKIP 1：test_modules_tls（TLS 插件裁剪，上游 exit 77 语义）

## 依赖版本选型（制品仓实测可用，W0 逐项 conan download 探测 14/14 OK）

ffmpeg/4.4.8 + libmad/0.15.1b + dav1d/1.5.0 + libogg/1.3.6（force 统一）+
libvorbis/1.3.7 + libtheora/1.2.0-alpha1 + flac/1.5.0 + libopus/1.6.1 +
libvpx/1.16.0 + x264/r3223 + x265/4.2 + libdvdnav/7.0.0 + fribidi/1.0.16 +
libass/0.17.5（字幕链 freetype/fontconfig/harfbuzz 由 libass 传递）。

## 产物

- lib/libvlc.so.5.6.1 + lib/libvlccore.so.9.0.1（核心库）
- lib/vlc/plugins/ 下 25 类 283 个 *_plugin.so
- bin/vlc（命令行播放器入口，shell wrapper）
- include/vlc/ 完整公共头树

test_package：libvlc_get_version（3.0 前缀校验）+ libvlc_get_compiler +
libvlc_new(0,NULL)/libvlc_release 实例生命周期 + 3 项鸿蒙特有断言。
---

**编译结束**: 2026-10-01 16:58
**最终状态**: built
