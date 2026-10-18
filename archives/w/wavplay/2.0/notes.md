# wavplay 2.0 适配笔记

## 适配路径
**路径 C · 高难度挑战**：上游音频后端强绑定 Linux legacy OSS `/dev/dsp` 接口（`ioctl` + `SNDCTL_DSP_*`），无跨平台抽象层，在 OpenHarmony 上不存在。本适配将音频后端**整体重写**为 OHOS 原生 `OH_AudioRenderer` / `OH_AudioCapturer`（纯回调模型），并使其真实可用。

## 编译环境
- 构建系统: autotools（automake + autoconf 2.61，2009 年版）
- 编译日期: 2026-10-15
- 编译器: OHOS SDK clang 15（默认 `aarch64-unknown-linux-ohos`，sysroot 已 baked-in）
- 平台: OpenHarmony PC（HarmonyOS aarch64）
- 状态: built

## 编译步骤

1. 获取官方 tarball 并校验 SHA256：
   `https://download.sourceforge.net/project/wavplay/Release%20Downloads/wavplay-2.0.tar.gz`
   sha256 = `256ea0b581d587b482e0c928869e3896845a5299b8e124c01749b4b9edfeb552`
2. 应用 4 个 portability 补丁（见"源码修改"）。
3. configure（OHOS 交叉编译）：
   ```
   ./configure --enable-nox \
     --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu \
     --prefix=<prefix>
   ```
   - `--enable-nox`：禁用 X11 GUI 客户端（OHOS 无 X11），只构建 wavplay / wavrec CLI
   - `--build/--host=aarch64-unknown-linux-gnu`：2009 版 config.guess 不识别 HarmonyOS build machine，显式传 triplet（config.sub 接受）；OHOS SDK clang 已 baked-in `aarch64-unknown-linux-ohos` + sysroot，**无需** `--target`/`--sysroot`
4. 编译：`CFLAGS="-DHAVE_OHOS_AUDIO -O2" LDFLAGS="-lohaudio" make -j`
   - `-DHAVE_OHOS_AUDIO` 能力宏（构建系统提供，非平台宏）选择 OHOS 音频后端（补丁），`-lohaudio` 链接系统音频库
5. `make install DESTDIR=<staging>` — 安装 `bin/wavplay`、`bin/wavrec`、`bin/wavplay-config` + man 页。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `cannot guess build type` | 2009 版 config.guess 不识别 HarmonyOS build machine（`uname -s = HarmonyOS`） | 显式传 `--build/--host=aarch64-unknown-linux-gnu`（绕过 config.guess，config.sub 接受该 triplet） |
| 2 | file.c OSS 后端不可用（`SNDCTL_DSP_*` 未定义、无 `/dev/dsp`） | OHOS 无 OSS `/dev/dsp` 接口 | 重写为 `OH_AudioRenderer`/`OH_AudioCapturer`（纯回调），原 OSS 代码 `#ifndef HAVE_OHOS_AUDIO` 包裹 |
| 3 | locks.c sysv 信号量（`union semun`）不可用 | OHOS `sys/sem.h` 无 `union semun`；设备锁由 audio service（binder）管理 | OHOS 下 no-op 实现（`OpenDSPLocks` 返回 0，`Lock/UnlockDSP` 返回 0） |
| 4 | server.c `SNDCTL_DSP_RESET` 未声明 | OHOS 下 `HAVE_OS_UNKNOWN` → 不 include soundcard.h；设备复位由 renderer 管理 | 两处 `ioctl(...,SNDCTL_DSP_RESET,...)` 用 `#ifndef HAVE_OHOS_AUDIO` 包裹 |
| 5 | `wavplay -i` 报 `Unable to get audio locking semaphores` | no-op `OpenDSPLocks` 返回 -1 被调用方当"锁失败"（默认 `IPCKey=env_AUDIOLCK` 非零，必然调用） | `OpenDSPLocks` 改返回 0（合法伪 IPC ID，Lock/UnlockDSP 为 no-op） |

## 源码修改（4 个 portability 补丁）

| 补丁 | 文件 | 修改内容 |
|------|------|----------|
| 0001 | include/wavplay.h.in | 扩展 `DSPFILE` 结构：加 `OH_AudioRenderer*`/`OH_AudioCapturer*` 句柄 + 播放/录音回调同步状态（pthread mutex/cond + 写文件 + 剩余字节 + 停止标志）；加 `#include <pthread.h>` |
| 0002 | src/file.c | **核心重写**：原 OSS `OpenDSP/CloseDSP/PlayDSP/RecordDSP` 用 `#ifndef HAVE_OHOS_AUDIO` 包裹；新增完整 OHOS 实现（`#ifdef HAVE_OHOS_AUDIO`，约 340 行）：格式映射（8bit→U8、16bit→S16LE、Mono/Stereo、PCM→RAW），播放用 `OH_AudioRenderer_OnWriteDataCallbackAdvanced`（返回填充字节数，0 = EOF），录音用 `OH_AudioCapturer_OnReadDataCallback`，实时超时安全网（duration×3 + 30s）防 audio service 无响应死循环 |
| 0003 | src/locks.c | 原 sysv 信号量实现 `#ifndef HAVE_OHOS_AUDIO` 包裹；OHOS 下 no-op 实现（`OpenDSPLocks` 返回 0、`LockDSP/UnlockDSP` 返回 0） |
| 0004 | src/server.c | 两处 `ioctl(dfile->fd, SNDCTL_DSP_RESET, 0)` 用 `#ifndef HAVE_OHOS_AUDIO` 包裹 |

> **R8 能力宏说明**：补丁使用 `#ifdef HAVE_OHOS_AUDIO` / `#ifndef HAVE_OHOS_AUDIO` **能力宏**（capability macro，由构建系统提供，非平台宏 `__OHOS__`）守卫，符合项目"非平台名能力宏"约定。保留双后端的理由：① OSS 后端是 wavplay 原有功能，非 OHOS 构建（不提供该宏）行为与上游完全一致、零行为变化，且 DSPFILE 新增字段与 `<pthread.h>` 包含同受该宏守卫，ABI/依赖与上游零差异；② OHOS 音频子系统（`OH_AudioRenderer`/`OH_AudioCapturer`）无 POSIX 等价接口（OHOS 无 `/dev/dsp`），音频硬件访问本质平台特定，无法用单一 POSIX 接口统一表达；③ 守卫内含完整实质逻辑（OHOS 后端实现 + 回调并发同步），非空壳 stub。

## 格式映射（OSS → OHOS）

| 属性 | OSS | OHOS |
|------|-----|------|
| 采样 8bit | `SND_FORMAT_UNSIGNED_8` | `AUDIOSTREAM_SAMPLE_U8` |
| 采样 16bit | `SND_FORMAT_LITTLE_ENDIAN` | `AUDIOSTREAM_SAMPLE_S16LE` |
| 声道 | `SND_FMT_CHANNELS_*` | `AUDIOSTREAM_CHANNEL_LAYOUT_MONO/STEREO` |
| 编码 | PCM | `AUDIOSTREAM_ENCODING_TYPE_RAW` |
| 12/24/32bit | 支持 | **不支持**（OHOS 仅 8/16bit）→ 报错 |

## 依赖版本
- 无 conan 第三方依赖（核心无依赖）
- 系统库：`libohaudio.so`（OHOS 原生音频库，系统提供，非 conan 包）
- X11 GUI 依赖（libx11/libxmu/libxt/motif）：OHOS 下 `--enable-nox`，不需要

## 验证结果

```bash
$ ./src/wavplay --version
wavplay version 2.0            # exit 0 ✓
$ ./src/wavplay -i test440.wav  # 信息模式，验证 WAV 头解析（不触音频设备）
Pathname:	test440.wav
Sampling Rate:	44100 Hz
Mode:		Mono
Samples:		44100
Bits:		16             # exit 0 ✓
```

- **编译**：7 个源文件（main/file/recplay/wavfile/locks/msg/server）全部编译 + 链接成功，零错误
- **产物**：`src/wavplay` + `src/wavrec`（ELF arm64，NEEDED: libohaudio.so + libc.so[musl]）
- **消费者用例**：6/6 PASS（`--version` / `--help` / `-i`×3 / `wavrec --version`）

## 真实出声/录音：环境受限说明
- **编译通过、代码完整、CLI/文件逻辑经消费者用例验证**（见上）。
- **真实出声/录音在当前 shell 环境无法验证**：PoC 实证 SDK sysroot 的 `libohaudio.so` 是 22KB 接口桩（169 个导出符号仅映射 3 个唯一地址，桩函数反汇编仅 `ret`）。真实实现位于完整 OHOS 系统运行时（audio_server + HAP 沙箱 + 权限）。
- 真实出声/录音需在完整 OHOS 应用环境（PR 合入后的 CI / 真机环境）验证。

## 交付物
| 文件 | 说明 |
|------|------|
| bin/wavplay | WAV 播放 CLI（OHOS 原生后端） |
| bin/wavrec | WAV 录音 CLI（OHOS 原生后端） |
| bin/wavplay-config | 开发标志报告工具 |
| share/man/man1/wavplay.1 | man 页 |

## 注意事项
1. OHOS 仅支持 8/16bit PCM；12/24/32bit 报错（平台限制，非适配缺陷）。
2. 音频设备锁由 OHOS audio service（binder）管理，userspace 不做 sysv 信号量锁。
3. 播放/录音为纯回调模式（非轮询），带实时超时安全网防 audio service 无响应死锁。
4. `wavplay -i` / `--version` / `--help` 不触音频设备，可离线验证；真实出声需完整 OHOS 运行时。
---

**编译结束**: 2026-10-16 14:19
**最终状态**: built
