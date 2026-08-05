# audacious-plugins 4.5.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-05
- 编译器: clang/clang++
- 状态: built (conan create 失败，因部分依赖不在制品仓)

## 源码
- 官方源: https://distfiles.audacious-media-player.org/audacious-plugins-4.5.1.tar.bz2
- SHA256: f4feedc32776acfa9d24701d3b794fc97822f76da6991e91e627e70e561fdd3b

## 编译步骤

1. 源码解压到 ~/tmp/builds/audacious-plugins-4.5.1.work/
2. 应用补丁:
   - 0001-build-aux-config.guess.patch (HarmonyOS 平台检测)
   - 0002-build-aux-config.rpath.patch (rpath 平台兼容)
3. 设置环境变量:
   - LD_LIBRARY_PATH 包含 SDK lib 目录 (lld 依赖 libxml2.so.16)
   - PKG_CONFIG_PATH 包含 usr/local/lib/pkgconfig
   - TMPDIR 设置为 $HOME/tmp
4. configure (无裁剪，仅禁用不可用的 GTK/Qt UI):
   ```
   ./configure --prefix=$DEFAULT_PREFIX --disable-gtk --disable-qt
   ```
5. make -j1
6. make install DESTDIR=$TEST_PREFIX (staging)

## 与历史版本对比 (无裁剪改进)

| 功能 | 历史版本 (2026-05-29) | 当前版本 (2026-08-05) |
|------|----------------------|----------------------|
| Opus | ❌ --disable-opus | ✅ 已启用 |
| WavPack | ❌ --disable-wavpack | ✅ 已启用 |
| FFmpeg | ❌ --disable-ffaudio | ✅ 已启用 (使用 ffmpeg-full 共享库) |
| neon HTTP | ❌ --disable-neon | ✅ 已启用 (需 OpenSSL 3.5.6) |
| GTK | ❌ --disable-gtk | ❌ (gtk+-3.0 不可用) |
| Qt | ❌ --disable-qt | ❌ (Qt6Svg 不可用) |
| 插件总数 | 32 | 35 (+3) |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lld 找不到 libxml2.so.16 | musl 动态加载器不解析 RUNPATH 中的 $ORIGIN | LD_LIBRARY_PATH 包含 SDK lib 目录 |
| 2 | config.status 创建临时文件失败 | umask 077 在 HMDFS 上因 setgid 继承导致权限问题 | 修改 config.status 使用 umask 022 |
| 3 | config.h 缺少 EXPORT 定义 | autoheader 无法处理 AUD_COMMON_PROGS 宏 | 手动添加 EXPORT 等定义到 config.h |
| 4 | opusfile.h 找不到 | 预编译包将头文件放在错误位置 | 复制到 include/opus/ 目录 |
| 5 | wavpack.h 找不到 | 预编译包将头文件放在 include/ 而非 include/wavpack/ | 创建 wavpack/ 子目录并复制 |
| 6 | ffaudio 链接失败 (-fPIC) | ffmpeg 静态库不支持 PIC | 使用 ffmpeg-full 共享库 |
| 7 | neon 链接失败 (SSL_get1_peer_certificate) | neon 0.35.0 需要 OpenSSL 3.0+ | 安装 OpenSSL 3.5.6 |
| 8 | gdbus-codegen 无法运行 | shebang 指向 /usr/bin/python3 不存在 | 创建 wrapper 使用正确的 python3 路径 |
| 9 | pcre2/libffi 缺失 | glib 2.88.0 的传递依赖 | 安装 pcre2 10.40 和 libffi 3.4.6 |
| 10 | conan create 失败 | 多个依赖不在 ohpcd 制品仓 | 待专家分析，需先适配发布依赖 |

## 源码修改

- 0001-build-aux-config.guess.patch: 添加HarmonyOS识别
- 0002-build-aux-config.rpath.patch: 更新config.rpath以适配平台

## 依赖版本

- audacious: 4.5.1 (cmd-pkgs 预编译包)
- glib: 2.88.0 (cmd-pkgs)
- mpg123: 1.33.5 (cmd-pkgs)
- libvorbis: 1.3.7 (cmd-pkgs)
- flac: 1.4.3 (cmd-pkgs)
- alsa-lib: 1.2.12 (cmd-pkgs)
- libxml2: 2.15.3 (cmd-pkgs)
- opus: 1.4 (cmd-pkgs)
- opusfile: 0.12 (cmd-pkgs)
- ffmpeg-full: 8.1.1 (cmd-pkgs)
- wavpack: 5.8.1 (cmd-pkgs)
- neon: 0.35.0 (cmd-pkgs)
- openssl: 3.5.6 (cmd-pkgs)
- pcre2: 10.40 (cmd-pkgs)
- libffi: 3.4.6 (cmd-pkgs)
- libogg: 1.3.5 (cmd-pkgs)
- zlib: 1.3.1 (cmd-pkgs)

## Conan 制品仓依赖状态

**已在 ohpcd 制品仓:**
- glib/2.84.0.1, flac/1.4.3, libxml2/2.15.3.1, opus/1.5.2.1, opusfile/0.12, ffmpeg/8.1.2, zlib/1.3.2

**不在 ohpcd 制品仓 (需先适配发布):**
- audacious, mpg123, libvorbis, alsa-lib, wavpack, neon, openssl, pcre2, libffi, libogg

## 验证结果

```bash
# 35个插件.so文件正确安装
# Input(12): metronom, psf, psf2, tonegen, vtx, xsf, flac, vorbis, mpg123, console, opus, wavpack, ffaudio
# Output(3): alsa, oss4, filewriter
# Effect(10): background_music, bitcrusher, compressor, crossfade, crystalizer, echo, mixer, silence-removal, stereo, voice_removal
# General(2): mpris2, song_change
# Container(6): asx, asx3, audpl, m3u, pls, xspf
# Transport(2): gio, neon
# 48个locale .mo文件正确安装
```

## 注意事项

- GTK/Qt UI 禁用: gtk+-3.0 和 Qt6Svg 不在制品仓，待依赖发布后可启用
- ffaudio: 需使用 ffmpeg-full (共享库) 而非 ffmpeg (静态库，不支持 PIC)
- neon: 需 OpenSSL 3.0+ (neon 0.35.0 使用 SSL_get1_peer_certificate)
- conan create 失败: 需先适配发布 audacious, mpg123, libvorbis, alsa-lib 等依赖到 ohpcd 制品仓

---

**编译结束**: 2026-08-05
**最终状态**: built (本地编译通过，conan create 因依赖缺失失败)
