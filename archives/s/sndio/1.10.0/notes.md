# sndio 1.10.0 适配笔记（HarmonyOS PC / OHOS arm64）

## 结论

- 构建系统：**自定义 configure + Makefile.in**（`configure` 是纯 POSIX sh，不做编译器探测，靠 sed 从 `Makefile.in` 生成各目录 Makefile；顶层 `install:` 逐目录 `make install`）。
- 源码：`https://sndio.org/sndio-1.10.0.tar.gz`，sha256 `bebd3bfd01c50c9376cf3e7814b9379bed9e17d0393b5113b7eb7a3d0d038c54`，162725 B，108 文件，顶层目录 `sndio-1.10.0`。
- 产出：`lib/libsndio.so.7.3` + `libsndio.so`、`libsndio.so.7` 两个软链、`include/sndio.h`、`lib/pkgconfig/sndio.pc`、`bin/{aucat,sndiod,sndioctl,midicat}`。
- 上游**没有测试套件**（tarball 无 `regress/`），鸿蒙独有测试全部由 `test_package/` 承担。

## 三个补丁（都必要，均已用 `git apply --check` 验证可干净应用到纯净源码）

| 补丁 | 内容 | 为什么必须 |
|------|------|-----------|
| `0001-bsd-compat-bsd-compat.h.patch` | 把 `SOCK_CLOEXEC` 的兜底定义包进 `#ifndef` | OHOS/musl 头文件已定义该宏，重复定义会冲突 |
| `0002-bsd-compat-getpeereid.c.patch` | `struct ucred` 换成 `__OHOS__` 下的本地 `struct sndio_ucred` | musl 暴露的 `struct ucred` 在 OHOS 上不完整，直接取字段编译不过 |
| `0003-configure.patch` | 新增 `HarmonyOS)` 平台分支：`alsa=no`、`ldadd="-lm"`、`so_link="libsndio.so libsndio.so.${MAJ} libsndio.so.${MAJ}.0"`、`so_ldflags="-Wl,-soname=libsndio.so.${MAJ}"`、`defs='-D_GNU_SOURCE -DHAVE_SOCK_CLOEXEC -DHAVE_CLOCK_GETTIME'` | `configure` 用 `case \`uname\`` 选平台，没有 HarmonyOS 分支就落到 `esac` 之外（默认 `so=`/`so_ldflags=` 为空 → 不产 .so、无 soname） |

`-Wl,-soname` 是这里最关键的副作用：OHOS 工具链默认不给共享库打 soname，没有它下游 `DT_NEEDED` 会写死构建期绝对路径（生态级 L5 缺陷）。

## 构建命令（配方内部）

```sh
<CONFIG_SHELL> ./configure --prefix=<pkg> --mandir=<pkg>/share/man \
    --disable-alsa --disable-oss --disable-sun --disable-rmidi --disable-umidi \
    --enable-dynamic
make -j1 SHELL=<CONFIG_SHELL> CC=<clang> AR=<llvm-ar> RANLIB=<llvm-ranlib> CFLAGS="-O2 -fPIC"
make install SHELL=<CONFIG_SHELL> ...
```

- 构建约定：`configure` 与生成的 Makefile 都经 `CONFIG_SHELL`（OHOS 无 `/bin/sh`），默认 `/data/service/hnp/bin/bash`；
  `make -j1`；`CC/AR/RANLIB` 取自 `tools.build:compiler_executables`（profile 里是
  `/data/service/hnp/bin/clang`），不依赖 shell 环境里的 `${CC}`。
- 该 OHOS 版 conan **没有 `tools.build:ldflags`** 这个 conf（`conan config list` 实测），等价项是 `tools.build:sharedlinkflags` / `tools.build:exelinkflags`；`tools.build:cflags` 存在。

## 踩过的坑（全部实测）

1. **toybox `patch` 静默 no-op**：本机 `/usr/bin/patch` 是 toybox 0.8.12，对任何补丁报 RC=0 却不改文件。本地验证必须 `PATH=~/tmp/bin:$PATH`（busybox shim）或 `git apply --check`。配方里因此内置 `_assert_patches_applied()`：`build()` 在打补丁后检查 `configure` 里有 `HarmonyOS)`、`getpeereid.c` 里有 `sndio_ucred`、`bsd-compat.h` 里有 `ifndef SOCK_CLOEXEC`，缺一条就抛 `ConanException`，避免拿未打补丁的源码静默构建。
2. **`core.*` conf 不能在命令行传**：`-c core.sources:download_cache=...` 报 `'core.*' configurations are not allowed in profiles`。该值只能写 `~/.conan2/global.conf`（已在本机 global.conf 配好下载缓存目录）；离线喂源码时把 tarball 以 sha256 命名放进该目录即可按 hash 命中。
3. **`tools.build:ldflags` 不存在**（见上）。
4. **`aucat -e` 不是编码全名**：`-e raw` 报 `raw: bad encoding`。`-e` 走 `aparams_strtoenc()`，要 `s8/u8/s16/s16le/s24be...`；`raw/wav/aiff/au` 是 `-h` 的头类型。
5. **`sio_initpar()` 的哨兵值是 `~0u` 不是 `0xff`**：`sio.c` 做 `memset(par, 0xff, sizeof(*par))`，`struct sio_par` 字段都是 `unsigned int`，所以每个字段是 0xFFFFFFFF；实测打印确认（`bits=4294967295 ... magic=2209940900`, `sizeof=64`）。测试最初按字节写 `== 0xff` 是错的，已改为 `== ~0u` 并补一条 `__magic` 被真实写入的断言。

## 测试（鸿蒙独有，`test_package/`）

`conan create` 实测输出（一次通过，RC=0）：`RESULT OK: 0 failure(s)` + 24 条 `[ok]`
（另有 1 条 `SKIP: pkg-config --modversion`，worker 上无该二进制，汇总行也标出跳过数），覆盖：

- CMake 消费者工程编译并链接 `sndio::sndio`，24 个公开入口符号全部解析；
- `sio_initpar()` 全字段 `~0u` + `__magic` 非哨兵；
- `sio_open()` / `sioctl_open()` / `mio_open()` 对不存在的设备返回 NULL（不崩）；
- 安装布局：头文件、`sndio.pc`、四个 CLI、`libsndio.so{,.7,.7.3}`；
- **ELF 动态段纯 Python 解析**（不依赖 readelf）：消费者 `DT_NEEDED=libsndio.so.7, libc.so`，无任何含 `/` 的条目；
- `libsndio.so.7.3` 的 `DT_SONAME=libsndio.so.7`；
- `sndio.pc` 可重定位（`prefix=${pcfiledir}/.. /..`）+ `-lsndio`；
- **真实数据通路**：`aucat -n -e s16 -h raw -r 8000 -c 1 -i in.raw -o out.raw`，
  输出字节数**精确等于**输入（16000 B → 16000 B），且输出 RMS 实测 **8000**（与输入方波一致，
  断言阈值 RMS > 7200）；
- `aucat`/`sndiod`/`sndioctl`/`midicat` 四个二进制都能执行并打印用法串。

**未覆盖（如实记录）**：需要活着的 `sndiod` 的路径。沙箱无音频硬件，`sndiod -f` 只接受已存在的 sndio 设备，因此真实设备播放/录音无法测；测试对这些路径断言「干净返回 NULL」，不冒充通过。`pkg-config` 二进制在 worker 上不存在，版本查询未验证（配方打印 WARN，其余 .pc 内容检查照做）。

## 依赖

无 conan 依赖；只用系统 musl libc 与 `-lm`。ALSA/OSS/Sun/raw-MIDI/USB-MIDI 后端全部关闭（OHOS 不提供）。

## 源码修改说明

- **未修改上游测试用例**：1.10.0 的 tarball 不含 `regress/`，上游没有任何测试入口，
  因此不存在"上游测试用例修改"。
- 3 个补丁只涉及 `configure`（新增 HarmonyOS 分支）与 `bsd-compat/`
  （`SOCK_CLOEXEC` 宏兜底、`getpeereid` 的 `ucred` 结构），不触碰测试代码。
- 鸿蒙独有测试全部写在本仓 `test_package/`（新增目录，不改上游源码树）。

## 对话与决策记录

### 对话 #1 任务承接与起点核对

- 任务点名 **sndio 1.10.0**（`kmix 26.04.0` 的 automagic 音频后端之一，非硬依赖）。
- 归档目录原有 `manifest.yaml` + `notes.md` + 3 个补丁，**没有配方、没有 test_package**；
  旧 `notes.md` 还写着"configure 已内置 HarmonyOS 支持、无需修改源码"——与实测不符
  （`configure` 用 `case \`uname\`` 选平台，没有 HarmonyOS 分支，落到默认空 `so=`/`so_ldflags=`
  → 不产 `.so`、无 soname）。本轮按实测重写。
- 源码：`https://sndio.org/sndio-1.10.0.tar.gz`，sha256 `bebd3bfd…`，162725 B，108 文件。

### 对话 #2 补丁可用性实测（防 toybox patch 静默 no-op）

- 本机 `/usr/bin/patch` 是 toybox 0.8.12，对任何补丁报 RC=0 却不改文件。
  因此先对纯净源码跑 `git apply --check`：3 个补丁全部可干净应用；实际应用后逐项确认
  `HarmonyOS)`（configure 第 130 行）、`struct sndio_ucred`、`#ifndef SOCK_CLOEXEC` 是否存在。
- 结论：3 个补丁**都必要**，且配方内置 `_assert_patches_applied()` 在 `build()` 里断言，
  防止拿未打补丁的源码静默构建出无 soname 的库。

### 对话 #3 测试设计（上游无测试 → 鸿蒙独有测试）

- 上游 tarball 无 `regress/`，无任何上游测试入口。
- 沙箱无音频硬件，`sndiod -f` 只接受已存在的 sndio 设备 → 守护进程/真设备路径不可测。
- 改用 `aucat -n` 离线模式做真实数据通路：`-i`/`-o` 必须同时给，`offline()` 会把
  `dev_name` 设为 `offline` 并请求 `SIO_PLAY|SIO_REC`，数据真的走一遍 sndio 的缓冲与编码转换。
  16000 B raw s16 进 → 16000 B 出（字节数精确相等）、输出 RMS 与输入一致，是真实信号保真而非空壳断言。

### 对话 #4 两处测试假设被实测推翻（不粉饰）

1. `aucat -e raw` 报 `raw: bad encoding`：`-e` 走 `aparams_strtoenc()`，只认
   `s8/u8/s16/s16le/s24be…`；`raw/wav/aiff/au` 属于 `-h` 头类型。改为 `-e s16 -h raw`。
2. `sio_initpar()` 断言写 `== 0xff` 失败：`sio.c` 是 `memset(par, 0xff, sizeof(*par))`，
   字段都是 `unsigned int`，所以每个字段等于 **0xFFFFFFFF（`~0u`）**。本地重建库跑探针实测
   `bits=4294967295 … magic=2209940900, sizeof=64`，随后按实测值改断言，并补一条
   `__magic` 非哨兵的断言。
   —— 若把断言放宽成 `!= 0` 就能"变绿"，但那等于掩盖，没做。

### 对话 #5 conan 环境口径

- `-c core.sources:download_cache=…` 被拒：`core.*` 只能写在 `~/.conan2/global.conf`
  （本机已配），离线时把 tarball 以 sha256 命名放进该目录即可命中。
- 该 OHOS 版 conan 没有 `tools.build:ldflags`，等价项为
  `tools.build:sharedlinkflags` / `tools.build:exelinkflags`。
- finish 的 W3 首轮报 3 个 L0 门禁：L0d（`test()` 无 `self.run()`）、L0e（缺
  `test_package/MANIFEST.yml`）、L0k（构建 bin/ 但缺 `archives/s/sndio/commands.json`）。
  三项都已按真实需要补齐（`self.run()` 用于真跑消费者程序与 aucat 通路，非占位）。

## 交付物打包

- `packaging/sndio-1.10.0-ohos-aarch64.tar.gz`：由官方打包工具
  (`scripts/ohc/package_builder.py`) 从 conan 包目录生成，17 个条目
  （`licenses/LICENSE`、头文件、`sndio.pc`、4 个 CLI、4 个 `.so` 条目）。
- `packaging/sndio-1.10.0-ohos-aarch64-debug.tar.gz`：同上工具 objcopy 出的 9 个
  `.debug` 符号文件（release 产物已 strip，调试符号单独成包）。
- `.staging-verified`：对包内 4 个二进制逐个执行并校验 usage 串，`verified=4 failed=0`
  （sndio 工具无 `--version`，方法已写在标记文件里）。
---

**编译结束**: 2026-10-17 10:14
**最终状态**: built
