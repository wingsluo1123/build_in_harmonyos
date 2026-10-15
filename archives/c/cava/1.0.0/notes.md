# cava 1.0.0 适配笔记

## 编译环境
- 构建系统: autotools（上游 tag 归档只有 `configure.ac`，无 `configure`，需自举）
- 编译日期: 2026-10-08
- 编译器: clang 15.0.4（profile `ci/conan/profiles/ohos-aarch64`，`tools.build:compiler_executables` 指 `/data/service/hnp/bin/clang`）
- 设备: HarmonyOS PC aarch64（`uname -s = HarmonyOS`，`uname -r = HongMeng Kernel 1.12.0`）
- CONAN_HOME: 独立 home，三步播种（`remotes.json` → `global.conf` 追加 `core.sources:download_cache` → `conan remote list` 自检见 `ohpcd`）
- 状态: **conan-verify 通过（本机分支 + CI 分支两轮实测均 PASS）**；L2/L4/L5 报告为「跳过（无 cache 路径）」⇒ 记 `skip` 不记 `pass`

## 形态与货源
- 终端音频频谱可视化：音频输入 → FFT（fftw3）→ ncurses/raw 终端渲染
- 语言: C99（实测 `.c = 23`）
- 货源（权威）: `https://codeload.github.com/karlstav/cava/tar.gz/refs/tags/1.0.0`
  - 实测 `HTTP 200` / `3353259 B`
  - `sha256 = 2866cea11d0bd38406924ab2b47d5577f14909a7321ee928b6836391f375af7e`
  - codeload 该路径无 `.tar.gz` 后缀 ⇒ `conandata.yml` 显式给 `filename: cava-1.0.0.tar.gz`
  - ⛔ 不用 Debian 池址（PF7 黑名单）

## 编译步骤

1. `conan-init` 生成配方骨架 → 手工补齐 `conanfile.py` / `conandata.yml` / `test_package/` / 软件级 `commands.json`
2. `conan-verify`（内部 = `conan create`），`generate()` 阶段：
   - `AutotoolsToolchain` 注入 configure 参数（见下）
   - `AutotoolsDeps` 注入 `CPPFLAGS` / `LDFLAGS` / `LIBS`
   - `VirtualBuildEnv`
3. `build()`：
   - 修补生成的聚合 env 脚本（`SHELL`/`CONFIG_SHELL` 从 hnp bash 文本替换为 `/bin/sh`，见「遇到的问题」#4）
   - 预置依赖运行期 `LD_LIBRARY_PATH`（见 #1）
   - 补 `version` 文件（`1.0.0`，上游 `autogen.sh` 才生成，而 `configure.ac` 用 `m4_esyscmd_s([cat version])` 取 `PACKAGE_VERSION`）
   - `autoreconf -fi` 自举（**不直接跑 `./autogen.sh`**：CI worker 拒绝执行 shebang 脚本，`适配检查清单` Autotools #8）
   - `configure` 实际命令（`conan create` 日志原文）：

     ```text
     "<src>/configure" --prefix=/ '--bindir=${prefix}/bin' '--sbindir=${prefix}/bin'
       '--libdir=${prefix}/lib' '--includedir=${prefix}/include' '--oldincludedir=${prefix}/include'
       --disable-input-alsa --disable-input-pulse --disable-input-pipewire
       --disable-input-portaudio --disable-input-sndio --disable-input-oss
       --disable-input-jack --disable-input-coreaudio --disable-input-coreaudio-tap
       --disable-output-sdl
       --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos
     ```
   - `make -j1` → `make check` → 上游 `cavacore_test` → 上游 `test_configs` 运行期断言
4. `package()` = `autotools.install()` + 兜底清理 `.la`

### configure 实测探测结果（`reports/conan-create.log`，**第 9 轮 = CI 分支真重建**，即第 8 轮同配置的补归档重跑）
```text
checking for pthread_create in -lpthread... yes
checking for sqrt in -lm... yes
checking for fftw_execute in -lfftw3... yes
checking for ncursesw6-config... (cached) no        ← CI 分支：`ac_cv_path_CURSES_CONFIG=` 预置空 ⇒ 不取 PATH 上的 ncursesw6-config
checking for initscr in -lncursesw... yes
checking for curses.h... yes
checking for libiniparser... no          ← 上游 .pc 名为 libiniparser，实物是 iniparser.pc ⇒ 走 AC_CHECK_LIB 回退
checking for iniparser_load in -liniparser... yes
iniparser > 3.2 test OK
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot run C compiled programs.`（`Error loading shared library libfftw3.so.3` / `libfftw3_threads.so.3`，`./conftest` 退出 127） | **fftw 以共享库交付**（实物 `lib/` 只有 `libfftw3.so*`、无 `.a`；iniparser 与 ncurses 是 `.a`），而 `Autotools.configure()` 走 `run(env="conanbuild")`，conanbuild 内没有依赖 runenv ⇒ configure 阶段 autoconf 真跑 conftest 时动态加载器找不到 `.so` | `build()` 开头把**含 `.so` 的依赖 libdir** 预置进进程 `LD_LIBRARY_PATH`；conanbuildenv 的 `LD_LIBRARY_PATH=…${VAR:+:$VAR}` 是追加形态，不会覆盖 profile 的 llvm/lib（仓内先例 `4ti2/1.6.10`、`acedb/4.9.62`） |
| 2 | `config.guess: unable to guess system type` + `config.guess[1741]: can't create …/cgXXXXXX/dummy.c: Permission denied`，`configure: error: cannot guess build type; you must specify one` | ① `uname -s = HarmonyOS`，`config.guess(2024-07-27)` 不认识；② 其回退编译探针落在 `config.guess:119-121` 三处 **`(umask 077 && …)`** 的临时目录里，HMDFS 下该目录不可写 | 按 `适配检查清单` **Autotools #4** 显式给 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`（`config.sub(2024-07-27)` 实测接受 `aarch64-unknown-linux-ohos`；`configure.ac` 实测**无 `AC_RUN_IFELSE`**，给 `--host` 不吃掉运行期探测）。⚠ 见下「`E205` 口径分歧」 |
| 3 | `./config.status[1013]: can't create ./confXXXXXX/subs1.awk: Permission denied` → `config.status: error: could not setup config files machinery` | `configure:18406/18411` 两处 **`(umask 077 && mktemp -d "./confXXXXXX")` / `(umask 077 && mkdir "$tmp")`**；HMDFS 下 `umask 077` 得到 `drwx--S---`，当前进程（`uid=20020084`）写不进（**E011** 原始签名） | 按 **`E011`/`E114` 受控方案**（`手册/07 §12.1`）：`autoreconf -fi` **之后**对生成的 `configure` 做 `umask 077` → `umask 022` 文本改写，**保留真实临时目录创建、只改权限位**；不 patch 上游、不进 `patches/`。对照探针（本机实测）：`umask 077 → drwx--S--- → touch Permission denied`；`umask 022 → drwxr-s--x → OK` |
| 4 | profile 把 `SHELL` / `CONFIG_SHELL` 绝对钉到 `/data/service/hnp/bin/bash` | hnp bash 在 HMDFS 构建目录下 `getcwd` 必挂（E386 家族） | `适配检查清单` **Autotools #11**：对生成的聚合 env 脚本做**文本替换** `/data/service/hnp/bin/bash → /bin/sh`；⛔ 不用二次 `save_script` 打补丁（聚合器自 source 会无限递归） |
| 5 | 无 `version` 文件 ⇒ `PACKAGE_VERSION` 为空、`cava -v` 会打空版本 | 上游 `version` 不在 tag 归档里，由 `autogen.sh` 的 `echo 1.0.0 >version` 生成 | `build()` 内 `autoreconf` 前先写 `version = 1.0.0` |

### `E205` 口径分歧（必须留痕，审查若挑有据可答）
- `E205.rec_approach` 写「**Never use --build/--host flags as workaround**」；
- 但 `经验文档/手册/07-技术速查.md` §12.1 与 `经验文档/经验库/12b` 明确建议**显式 `--build`/`--host` 三元组**，`经验文档/适配检查清单.md` **Autotools #4** 就是这么落方的。
- **本包按 `适配检查清单` Autotools #4（依据 `12b §12.21`）执行**，与 `E205` 描述的老情形**不同**：老情形是 `config.sub` 与 `config.guess` **都不认**目标三元组；本包实测 `config.sub(2024-07-27)` **认** `aarch64-unknown-linux-ohos`（三候选实测：`aarch64-unknown-linux-ohos → aarch64-unknown-linux-ohos`、`aarch64-unknown-linux-gnu → aarch64-unknown-linux-gnu`、`aarch64-linux-ohos → aarch64-unknown-linux-ohos`），属**新情形**，清单口径适用。
- 真正卡住本包的 `config.guess` 根因是上面 #3 的 **HMDFS `umask 077`**（`经验库/05-Autotools-HMDFS-musl.md §54` 预判同款），不是三元组不被识别。

## 源码修改
- **无上游补丁**，`patches/` 为空，`conandata.yml` 的 `patches: {}`。
- 构建期对**生成物** `configure` 的受控改写（`umask 077 → 022`）属 `E011/E114` 受控方案，**不进 `patches/`、不改上游源文件**。**`E011` 落点同时含生成的 `configure`（`conanfile.py:218` → `source_folder/configure`）与 `config.guess`（`conanfile.py:225` → `source_folder/config.guess`）**，两者均由 `autoreconf -fi` 生成、**上游 tarball `tar tzf` 对 `configure` / `config.guess` / `config.sub` / `version` 全 0 命中**；`patches/` 为空、`conandata.yml` 的 `patches: {}`，**未改任何非生成物**（`conanfile.py:239` 的 `save(version)` 写的 `version` 同为 `autogen.sh` 生成物）。

## 依赖版本（W0 实测，`preflight_check.sh --deps` 真实版本）

| 依赖 | 版本 | W0 `preflight --deps` | 用途 | 是否进 `requires` |
|------|------|------------------------|------|--------------------|
| `fftw` | `3.3.11` | `[OK] 已发布` | `configure.ac:341` 硬依赖（`AC_MSG_ERROR`） | ✅ |
| `iniparser` | `4.2.6` | `[OK] 已发布` | `configure.ac:518` 硬依赖（`AC_MSG_ERROR`） | ✅ |
| `ncurses` | `6.6` | `[OK] 已发布` | 终端渲染（`output_ncurses` 默认开） | ✅ |
| `alsa-lib` | `1.2.16` | `[OK] 已发布` | —— | ❌ 按能力面裁剪，不进 |
| `pulseaudio` | `17.0.1` | `[OK] 已发布` | —— | ❌ 按能力面裁剪，不进 |
| `alsa-lib` | `1.2.12` | `[FAIL] 未发布` | —— | ❌ 未使用（`conan download … --only-recipe` 与 `preflight` 双向一致） |

工具依赖（`build_requirements`）：`automake/1.18`、`libtool/2.5.4`、`pkg-config/0.29.2`（三者按 `ohos-aarch64` profile 实测 **binary 可得**；`pkg-config` 提供 `share/aclocal/pkg.m4` 供 `PKG_CHECK_MODULES` 自举）。
⚠ `autoconf/2.72` **不能**进 `tool_requires`：实测其依赖 `perl/5.42.2` 在 ohpcd **Not found** ⇒ 用设备 `/data/service/hnp/bin/autoreconf`（autoconf 2.72，`init-build` 环境检查已核）。

## 能力面披露（音频输入，`appres` X 面披露模式）

**实测读数（B 机，2026-10-08）**
1. `ls -ld /dev/snd` → **`Permission denied`**（**不是 No such file** ⇒ 节点存在但不可访问）
2. `cat /proc/asound/cards` → **2 张声卡**：`0 [pcmachinecard]: pc-machine-card`、`1 [audiodp]: audio-dp`
3. `cat /proc/asound/pcm` → 多个 PCM **带 `capture 1`**（`00-00/00-01/00-05/00-06/00-08/00-09`）
4. `exec 3<>/dev/snd/controlC0` → **`Permission denied`**
5. 身份 `uid=20020084 gid=20020084 groups=20020084,1006(file_manager),1007(log),1097(netsys_socket),3009(readproc),3099(shader_cache)` —— **不含音频相关组**
6. Pulse：`/run/user` **不存在** ⇒ pulse socket 无；pipewire / jack / sndio / `/dev/dsp` 均无

**结论口径（照抄）**：ALSA 子系统存在（`/proc/asound/cards` 2 张卡：`0 [pcmachinecard]`、`1 [audiodp]`；`/proc/asound/pcm` 多个 PCM 带 `capture 1`），**但 `/dev/snd` 对本进程 `EACCES`（`uid=20020084`、`groups` 无音频组）⇒ 运行期无法打开采集节点**；`/run/user` 不存在 ⇒ **Pulse 真缺失**；pipewire/jack/sndio/`/dev/dsp` 均无。

**裁剪处置（上游原生支持，不是 hack）**
- 上游 `Makefile.am` 把 `input/fifo.c` + `input/shmem.c`（file/FIFO 输入）与 `output/terminal_noncurses.c` **无条件编入**；
- alsa/pulse/pipewire/portaudio/sndio/oss/jack 全部由 `configure` 的 `AC_CHECK_LIB`/`PKG_CHECK_MODULES` 探测，失败仅 `AC_MSG_NOTICE` 降级（`configure.ac:104-323`）；
- 故按实物能力 `--disable-input-*` 裁到 **file/FIFO 输入 + ncurses 渲染**；`config.c:925` 的 `default_input` 在无高优先级后端时**回落 `INPUT_FIFO`** ⇒ 裁剪后默认输入仍可用，程序功能完整。

**各输入后端在本设备不可用的原因**
| 后端 | 状态 | 原因 |
|------|------|------|
| alsa | 编译期裁剪 + 运行期不可用 | `/dev/snd` 对本进程 `EACCES`（无音频组），无法打开采集节点 |
| pulse | 编译期裁剪 + 运行期真缺失 | `/run/user` 不存在，无 pulse socket |
| pipewire | 编译期裁剪 + 运行期真缺失 | 无 `pipewire-0` socket |
| jack | 编译期裁剪 + 运行期真缺失 | 无 jack 服务/设备 |
| sndio | 编译期裁剪 + 运行期真缺失 | 无 `/dev/sndio*` |
| oss | 编译期裁剪 + 运行期真缺失 | 无 `/dev/dsp` |
| portaudio / coreaudio | 编译期裁剪 | 上游仅 macOS 有 coreaudio；portaudio 同属外部采集设备族 |
| **fifo / shmem（file 输入）** | **✅ 编入且可用** | 上游 `Makefile.am` 无条件编入，不依赖音频设备节点 |

## 测试数字（`手册/04 §10` 四类 + `§12.72` 资产口径，**五维落数值、三处同源**）

**五维账本**
| 维度 | 数值 | 口径与来源 |
|------|------|------------|
| `N_static`（上游静态/资产总数） | **10** | `cavacore_test.c` **1** + `run_all_tests.sh` **1** + `example_files/test_configs/*` **8**；示例程序 `.c` **0** |
| `N_registered`（构建系统注册可执行目标） | **0** | `Makefile.am` 无 `TESTS`/`check_PROGRAMS`；`make check` target 存在、跑 0 用例 |
| `N_executed`（本版实际执行） | **3** | ① `make check`（注册 0 项）② `cavacore_test` ③ `test_configs/{fifo_zero_test,non_zero_test}`；`N_runner` = 1（`cavacore_test` 内含 20 频点 × 上下界 2 = **40** 条 blueprint 比对断言） |
| 未执行 | **7** | 见下分类数值 |
| `N_consumer`（新增消费者测试） | **4** | `test_package/test.sh` 4 条断言（二进制定位 / `-v` 版本契约 / `--help` 三要素 / 非法选项非零退出） |

**`not_executed_categories`（未执行 7 项，按原因分类落数值）**
| 分类 | 数值 | 具体项 |
|------|------|--------|
| 输入后端按实物能力裁剪（编译期未编入） | **5** | `alsa_zero_test`、`pulse_zero_test`、`pipewire_zero_test`、`portaudio_zero_test`、`sndio_zero_test` |
| 需外部数据源（本设备无该服务） | **1** | `shmem_zero_test`（上游注释明示需 `squeezelite -v -m 51:fb:32:f8:e6:9f -z`） |
| 顶层测试脚本（其 8 个子配置中 6 个同上不可执行） | **1** | `run_all_tests.sh` |
| **合计** | **7** | = 8 个 `test_configs` − 已执行 2，再 + `run_all_tests.sh` |

**已执行 3 项是什么断言**
- `cavacore_test`：仿真模式（不定义 `AUDIO_INPUT`，**不碰任何音频设备**）自产 200Hz/2000Hz 正弦，跑 300 次 `cava_execute`，左右声道各 10 频点与 `blueprint` 逐点比对 ±2%，不符 `exit 1`（`cavacore_test.c:132-154`）；
- `fifo_zero_test`：`input=fifo source=/dev/zero`、`output=raw`、`draw_and_quit=60`，`zero_test` 断言总条高为 0（`cava.c:1721`）；
- `non_zero_test`：`input=fifo source=/dev/urandom`、`output=raw`，`non_zero_test` 断言总条高非 0（`cava.c:1725`）。
  后两项 `output=raw` ⇒ **不需要 tty、不碰 `/dev/snd`**，且与上游 CI `.github/workflows/build-and-test.yml` 实际跑的 4 项中的 2 项（`fifo`/`non_zero`）同源。

## 验证结果

### W0 依赖预检（实测）
```bash
bash ci/scripts/preflight_check.sh cava/1.0.0 \
  --deps "fftw/3.3.11 iniparser/4.2.6 ncurses/6.6 alsa-lib/1.2.16 pulseaudio/17.0.1"
# → [OK] 所有依赖均已发布到制品仓，可以安全开始适配 cava/1.0.0
# 对照组: --deps "alsa-lib/1.2.12" → [FAIL] 有 1 个依赖未发布（故未使用该版本）
```

### W3 conan-verify（实测，两轮分支均过）
| 轮次 | 分支 | 结果 | 关键证据 |
|------|------|------|----------|
| 第 5 轮 | 本机分支（PATH 上有 harmonybrew `ncursesw6-config`） | **PASS** | `checking for ncursesw6-config... <HOME>/.harmonybrew/bin/ncursesw6-config`、`initscr in -lncursesw... yes`、`curses.h... yes`（本机分支 harmonybrew 证据的落盘出处：`reports/w3-local-ci.log:359`） |
| 第 8 轮 | **CI 分支**（`ac_cv_path_CURSES_CONFIG=` 预置空 ⇒ 无 `ncursesw6-config`，只加环境变量、**未改配方**） | **PASS** | `checking for ncursesw6-config... (cached) no`、`initscr in -lncursesw... yes`、`curses.h... yes` |

⇒ **本机分支与 CI 分支（`CURSES_CONFIG` 空、头/库全部来自 conan `ncurses/6.6`）均已实测通过**，不靠推理。

CI 分支轮为**真重建**（非缓存命中），读数：
- `reports/conan-create.log`：**429 行**、`grep -c "Calling build"` = **1**、`grep -c "Building from source"` = **1**、`grep -c "ncursesw6-config"` = **1**、`grep -c "checking for ncursesw6-config... (cached) no"` = **1**（`§12.84②` 自检段口径；2026-10-08 03:51 第 9 轮实测）
- 第 6/7 轮曾是 `Already installed!` 缓存命中（128 行、`Calling build`=0）⇒ 按 `§12.84①` 先核 `dlcache` 有 `s/2866cea1…af7e` + `.json` sidecar（且 sidecar `references` 指向官方 codeload URL），再 `conan remove "cava/1.0.0@ohpcd/stable:*" -c` 清二进制后重跑。
- **当前盘上这份 `reports/conan-create.log` = 第 9 轮**（归档 mtime `03:51:20`、与 `conan-verify-report.md` Date `03:51:22` **同一轮**）：第 8 轮（CI 分支真重建）的日志曾被其后一次**缓存命中**轮（`finish` 内的 conan-verify，02:51:28）覆盖成 128 行 `Already installed!` 版 ⇒ 按上一条清二进制后以**同配置**（`ac_cv_path_CURSES_CONFIG=`、⛔ 未改配方）重跑第 9 轮补回，使 429/`Calling build`=1/`Building from source`=1/`(cached) no`=1 与 `conan-verify-report.md` 落在**同一轮**、可在盘上复算。

**G0–G4 + L2/L4/L5 判决（`reports/conan-verify-report.md`）**
```text
G0: ✅ PASS   （知识命中 E490，非阻塞）
G1: ✅ PASS   （name/version/source/build/package/package_info/export_sources/补丁调用/conandata/test_package/MANIFEST 全齐）
G2: ✅ PASS   （conan create 成功）
G3: ✅ PASS   （无 lib/ 目录（纯可执行包）→ 无系统同名库冲突，R26 通过）
G4: ✅ PASS   （⚠ 报告同时印 "无法找到程序包 ID"）
L2: ⏭️ 跳过（无 cache 路径）→ **记 skip，不记 pass**
L4: ⏭️ 跳过（无 cache 路径）→ 记 skip
L5: ⏭️ 跳过（无 cache 路径）→ 记 skip
```

**上游测试与消费者测试实测（`conan-create.log` 逐行）**
```text
make: Nothing to be done for 'check'.                       ← automake 注册 0 项（N_registered=0）
[cavacore_test] CC=/data/service/hnp/bin/clang
[cavacore_test] 复用 automake 对象 cava-cavacore.o
RUN: ./cavacore_test
matching blueprint                                          ← 蓝图 ±2% 断言通过（N_executed 之一）
[cava] 上游配置测试 fifo_zero_test: PASS（退出码 0）
[cava] 上游配置测试 non_zero_test: PASS（退出码 0）
PASS 1: 二进制定位 -> .../p/bin/cava
PASS 2: -v -> cava 1.0.0
PASS 3: --help 用法/描述/选项齐全
PASS 4: 非法选项 -> exit 1 + 错误信息
test cava 1.0.0: 4/4 checks PASS                            ← N_consumer=4（4 断言）
```

**数字三处同源声明**：本文件 / `manifest.yaml:tests` / `test_package/MANIFEST.yml` 三处的
`N_static=10`、`N_registered=0`、`N_executed=3`、`n_not_executed=7`（分类 5+1+1）、`N_consumer=4` 完全一致。

## 注意事项
- `status` 报 `libXext` = **HMDFS 大小写幻影**，与本包无关，不动。
- `knowledge/recipes/catalog.tsv` 为本地可重建缓存，**不提交**。
- `finish`/`submit` 生成的 `.build-closed`/`.staging-verified`/`.conan-verified`/`.ci-result.json`/`TASK_CARD.md`/`reports/` 全部 `.gitignore` 覆盖，**留盘不提交**。
- 提交范围只允许 `archives/c/cava/`（配方六件 + 软件级 `commands.json`）与已核实的知识草稿；**绝不 `git add -A`**。
---

**编译结束**: 2026-10-08 02:51
**最终状态**: built
