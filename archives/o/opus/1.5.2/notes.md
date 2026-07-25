# opus 1.5.2 编译笔记（HarmonyOS PC · 原生 conan create）

## 定位

Opus 音频编解码库（RFC 6716），BSD-3-Clause。主要消费方是 FFmpeg 的 `--enable-libopus`：
FFmpeg 内建有 Opus **解码**器，但**编码**需外接 libopus（内建 opus 编码器质量与成熟度不足）。

## 关键适配

标准 autotools（有 `configure.ac`），无平台特异性坑。只做了两处常规处理：

1. **显式 `--build` / `--host` 用 musl 三元组**（`aarch64-unknown-linux-musl`）：
   设备默认 TMPDIR 在 HMDFS 上，`config.guess` 的 mktemp 子目录里新建 `.c` 会 `Permission denied`
   → `cannot guess system type`。给出显式三元组即跳过 config.guess。`build == host` 让 configure
   走**原生**路径（运行期探针可用），而非 cross 模式误用预置值。
2. **`--disable-doc --disable-extra-programs`**：doc 需 doxygen；extra-programs 是 `opus_demo`
   等示例，不进包。

## 真机验证结果（2026-07-25，设备 3QC0124C11000718）

裸 `conan create . -pr ohos-native` **rc=0，115s**，包体积 733K。

- `lib/libopus.so.0`，SONAME `libopus.so.0`，DT_NEEDED 仅 `libc.so`
- `.codesign` 段存在
- `include/opus/`、`lib/pkgconfig/opus.pc` 齐全

### test_package（真实编解码往返，非仅版本查询）

`opus_encoder_create(48000,2,OPUS_APPLICATION_AUDIO)` → `opus_encode` 一帧 20ms 非均匀 PCM
→ `opus_decoder_create` → `opus_decode`，实测输出：

```
opus: version=libopus 1.5.2  encode=362 bytes  decode=960 samples/ch  OK
```

断言：编码字节数 > 2；解码样本数**恰好** 960（= 20ms @48kHz）。测试直接链 `-lopus`（非 dlopen），
故 CI 的 L1e 破坏性反向验证（移走 lib/ 与 include/）会在编译/链接期失败，反向验证成立。

## 状态

built —— 真机 `conan create` + 真实编解码 test_package 全绿。
