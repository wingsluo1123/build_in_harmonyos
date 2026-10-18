# sndio

极简音频与 MIDI 框架（OpenBSD 出品），提供 `libsndio` 库与
`aucat` / `sndiod` / `sndioctl` / `midicat` 四个命令行工具。
本仓提供其在 HarmonyOS PC（OHOS arm64）上的 Conan 适配。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.10.0 | built | 见 `1.10.0/`：配方、3 个补丁、鸿蒙独有测试、测试报告 |

## 产物

```
include/sndio.h
lib/libsndio.so.7.3  lib/libsndio.so.7 -> libsndio.so.7.3  lib/libsndio.so -> ...
lib/pkgconfig/sndio.pc
bin/aucat  bin/sndiod  bin/sndioctl  bin/midicat
```

- `DT_SONAME = libsndio.so.7`（由 `configure` 的 HarmonyOS 分支注入 `-Wl,-soname`），
  因此下游链接后 `DT_NEEDED` 记的是裸 soname，不会写死构建机路径。
- `sndio.pc` 使用 `prefix=${pcfiledir}/../..`，可随包整体搬迁。

## 构建

```sh
conan create archives/s/sndio/1.10.0 --user=ohpcd --channel=stable \
    -pr:h=ohos-aarch64
```

配方要点：自定义 `configure` + Makefile 构建；`CONFIG_SHELL` 走
`/data/service/hnp/bin/bash`（OHOS 无 `/bin/sh`）；`make -j1`；
ALSA / OSS / Sun / raw-MIDI / USB-MIDI 后端全部关闭（OHOS 不提供）。

## 工具用法（OHOS）

```sh
aucat -n -e s16 -h raw -r 48000 -c 2 -i in.raw -o out.raw   # 离线转换/混音
aucat -i file.wav -o /dev/sndio0                             # 播放（需音频设备）
sndiod -f /dev/sndio0                                        # 起设备守护进程
sndioctl -m output.level=0.8                                 # 调音量（需运行中的 sndiod）
```

`-e` 是采样编码（`s8/u8/s16/s16le/...`），`-h` 才是文件头类型（`raw/wav/aiff/au`）——
两者不要混用。

## 测试

上游 1.10.0 不含 `regress/`，没有上游测试。鸿蒙独有测试在
`1.10.0/test_package/`（C 消费者契约 + 构建期包校验 + `aucat -n` 离线
真实数据通路 + ELF 动态段纯 Python 校验），由 `conan create` 自动执行，
详见 `1.10.0/reports/test-report.md`。

## 已知限制

- 沙箱无音频硬件，`sndiod` 守护进程与真实设备播放/录音路径无法测试；
  测试对这些路径断言"干净返回 NULL"，未冒充通过。
- worker 上无 `pkg-config` 二进制，`sndio.pc` 的版本查询未验证（内容已校验）。
