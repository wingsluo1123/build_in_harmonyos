# libu2f-host 1.1.10 适配笔记

## 编译环境

- 构建系统: GNU Autotools（官方发布 tarball 自带 `configure`/`Makefile.in`）
- 目标平台: HarmonyOS PC / aarch64（`os=OHOS`, `arch=armv8`, clang 15）
- 编译器: clang/clang++（OHOS SDK）
- 依赖: json-c/0.17、hidapi/0.14.0（→ libusb/1.0.27），均来自 Conan 制品仓 ohpcd
- 补丁: 0 个（全部通过构建期环境变量/时间戳处理）

## 依赖链

```
libu2f-host/1.1.10
├── json-c/0.17        (pkg-config: json-c)
└── hidapi/0.14.0      (pkg-config: hidapi-libusb, lib: libhidapi-libusb)
    └── libusb/1.0.27  (pkg-config: libusb-1.0, lib: libusb-1.0)
```

上游 `configure.ac` 的 pkg-config 探测：
- `PKG_CHECK_MODULES([LIBJSON], [json-c], [], [PKG_CHECK_MODULES([LIBJSON], [json])])`
- `PKG_CHECK_MODULES([HIDAPI], [hidapi], [], [PKG_CHECK_MODULES([HIDAPI], [hidapi-hidraw])])`

而 Conan 制品仓中的包提供的是 `json-c.pc` 与 `hidapi-libusb.pc`。
`hidapi-libusb` 既不是 `hidapi` 也不是 `hidapi-hidraw`，直接 pkg-config 会失败。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess`/`config.sub` 不识别 HarmonyOS | tarball 内为 2019 版 autotools 脚本，无 `ohos` 目标 | configure 显式传 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu` |
| 2 | `PKG_CHECK_MODULES([HIDAPI],[hidapi])` 找不到包 | Conan hidapi 包只提供 `hidapi-libusb.pc` | 注入 `HIDAPI_CFLAGS`/`HIDAPI_LIBS` 覆盖变量（PKG_CHECK_MODULES 在变量已设时跳过 pkg-config） |
| 3 | `#include <hidapi.h>` 找不到头文件 | hidapi 头文件装在 `include/hidapi/hidapi.h` | `HIDAPI_CFLAGS=-I<pkg>/include/hidapi` |
| 4 | `#include <json.h>` 找不到头文件 | json-c 头文件装在 `include/json-c/json.h` | `LIBJSON_CFLAGS=-I<pkg>/include -I<pkg>/include/json-c` |
| 5 | `help2man` 不可用（OHOS 无此工具） | `src/Makefile.am` 的 `dist_man_MANS = u2f-host.1` 依赖 help2man 再生 | tarball 自带 `src/u2f-host.1`，构建前 `os.utime()` 刷新时间戳，令其比 `u2f-host.c`/`configure.ac` 新，跳过再生规则 |
| 6 | `gengetopt` 不可用 | `src/cmdline.{c,h}` 的再生规则依赖 gengetopt | tarball 已自带生成的 `src/cmdline.c/h`，同样刷新时间戳跳过规则 |
| 7 | musl libc 缺符号 | 依赖共享库引用了 musl 缺失的符号 | `LDFLAGS=-Wl,--allow-shlib-undefined`（与 libu2f-server 同法） |

## 关键构建配置

```python
tc.extra_ldflags.append("-Wl,--allow-shlib-undefined")
tc.configure_args += ["--build=aarch64-unknown-linux-gnu", "--host=aarch64-unknown-linux-gnu"]
env.define("LIBJSON_CFLAGS", f"-I{jinc} -I{jinc}/json-c")
env.define("LIBJSON_LIBS",   f"-L{jlib} -ljson-c")
env.define("HIDAPI_CFLAGS",  f"-I{hinc}")
env.define("HIDAPI_LIBS",    f"-L{hlib} -lhidapi-libusb -L{ulib} -lusb-1.0")
```

## 源码修改

无补丁文件；仅在 `build()` 中刷新 `src/u2f-host.1` / `src/cmdline.c` / `src/cmdline.h`
的 mtime（构建期行为，不改变仓库内容）。

## 产物

- `lib/libu2f-host.so` + `lib/libu2f-host.a`
- `bin/u2f-host`（CLI）
- `include/u2f-host/u2f-host.h`（公共头）
- `lib/pkgconfig/u2f-host.pc`
