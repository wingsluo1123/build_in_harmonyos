# svox

SVOX Pico **离线小 footprint 语音合成引擎**（随 Android AOSP 发布，
支持德/英/西/法/意）。本包产出 C 库 `libttspico`、命令行工具
`pico2wave` 与 lingware 语音数据。

## 它做什么

把文本变成语音 WAV（离线，不联网）：

```
$ pico2wave -l en-US -w hello.wav "hello world"
```

C 程序直接链库调 API（`picoapi.h`）：`pico_initialize` →
`pico_loadResource` → `pico_createVoiceDefinition` →
`pico_newEngine` → `pico_putTextUtf8`/`pico_getData` →
`pico_terminate`（完整序列见 `picoapi.h` "Basic_Usage"）。

## 快速验证

```c
#include <picoapi.h>
#include <picodefs.h>

static unsigned char mem[4 * 1024 * 1024];

pico_System system = NULL;
pico_initialize(mem, sizeof(mem), &system);  /* -> PICO_OK */
pico_terminate(&system);                     /* -> PICO_OK */
```

以上正是本包消费者测试（13 条断言）的核心路径 ——
零 lingware、零音频设备即可验证库的真实装载与系统生命周期。

## 版本

| 版本 | Conan 引用 | 状态 |
|---|---|---|
| 1.0 | `svox/1.0` | 已适配（aarch64，待真机预检） |

## 授权

代码 Apache-2.0。Debian 把二进制包划入 `non-free` 是因为 lingware
语音数据文件的授权问题，不是代码授权问题。
