# mednafen 1.32.1 适配笔记（HarmonyOS PC / aarch64）

> 本文件是**内部件**：含本机路径、槽位、命令与逐条读数；PR 正文只放模板白名单章节。

## 交付对象

- 上游：Mednafen 1.32.1（多机种模拟器，C++ / autotools）
- 官方直链：`https://mednafen.github.io/releases/files/mednafen-1.32.1.tar.xz`
- sha256：`de7eb94ab66212ae7758376524368a8ab208234b33796625ca630547dbc83832`（本地 tarball
  3571236 B，`xz -t` 通过；manifest.yaml / conandata.yml 与本行同源）
- 归档：`archives/m/mednafen/1.32.1/`（conanfile.py / conandata.yml /
  patches/×5 / test_package/{conanfile.py,test.sh,MANIFEST.yml}）
- 软件级：`archives/m/mednafen/commands.json`（R38，产物是 CLI）
- 分支：`feat/mednafen-1.32.1`；CONAN_HOME：`~/tmp/ch/home-主理-11-mednafen`
- 源码树：`~/tmp/builds/mednafen-1.32.1.{orig,work}`；VPATH 构建目录
  `~/tmp/builds/mednafen-1.32.1-build`

## 路径与资质

**路径 C（高难度挑战）**。资质按 `手册/03 §6.3` 四条取 ③：
**含汇编 + 周期精确（cycle-accurate）模拟架构**——真机解包后实测 `asm` 源文件 5 个
（CPU 核汇编），`cpp` 675 / `c` 103 / `h` 584 / `hpp` 89（总 2028 文件），
构建系统 autotools（configure 22643 行）；注册的模拟模块表实测 22 个
（`Emulation modules: apple2 nes snes gb gba pce lynx md pcfx ngp psx ss ssfplay
vb wswan sms gg sasplay snes_faust pce_fast demo cdplay`）。
PR 标题用**单一**前缀 `【高难度挑战】`（不叠加、不用知识前缀）；C Issue 由主理按
模板提复审，链主不建 Issue、不提审。

## 依赖面（W0 实测）

`conan download <精确引用> -r=ohpcd --only-recipe`（⛔ 未用通配 `conan list`），B 机实测：

| 引用 | 结果 |
|---|---|
| zlib/1.3.1.1 | OK |
| sdl2/2.30.10 | OK（另有 2.32.10 亦 OK，本包取 2.30.10） |
| flac/1.5.0 | OK |
| zstd/1.5.7 · lzo/2.10 · libiconv/1.17 · gettext/0.22.5.1 · libogg/1.3.6 · libvorbis/1.3.7 · libmad/0.15.1b · libsndfile/1.2.2 · libcdio/2.3.0 | OK（**候选复核项，最终未进 requires**） |

`requires()` 只声明 **configure.ac 里写死的三条**（不是猜测，逐条给出出处）：

| 依赖 | configure.ac 出处 | 性质 |
|---|---|---|
| zlib/1.3.1.1 | `:96 AC_CHECK_LIB([z],[zlibVersion], …, AC_MSG_ERROR([*** zlib not found!]))` | 硬依赖 |
| sdl2/2.30.10 | `:872-883 if $NEED_SDL → AM_PATH_SDL2(2.0.5)`；宏体 `m4/sdl2.m4:32-35` 先 `PKG_CHECK_MODULES([SDL],[sdl2 >= 2.0.5])` | 硬依赖 |
| flac/1.5.0 | `:709-716 --with-libflac` 默认 yes → `PKG_CHECK_MODULES(FLAC, flac >= 1.3.0)` | 默认开启的硬依赖 |

**未声明**的候选（复核后确认 configure.ac 里没有对应探测）：libsndfile / libcdio /
libvorbis / libogg / libmad —— mednafen 这些解码面走**源码树自带实现**
（`src/tremor`、`src/mpcdec`、`src/zstd`、`include/minilzo_internal` 等），
`--with-external-*` 默认全 no。zstd/lzo/libiconv 同理（zstd/lzo 有 `--with-external-*`
但默认 no；iconv 走 musl libc 自带 `iconv()`，实测 `checking for iconv... yes`）。
ALSA/JACK 在 OHOS 上不存在，但上游对两者都是**优雅降级**（`AM_PATH_ALSA` 失败只把
`have_alsa` 置 no；JACK 走 `PKG_CHECK_MODULES` 的 ACTION-IF-NOT-FOUND）⇒
`include/config.h` 实测 `HAVE_ALSA` / `HAVE_JACK` 均 undef，不加 `--disable-*`（R1）。

`bash ci/scripts/preflight_check.sh mednafen/1.32.1` 首次运行报「未找到依赖声明
（conanfile.py 尚未生成）」；配方落盘后本文件的依赖表即为其 W0 复核结论。

## 编译步骤（唯一入口 = 一次 conan create）

```bash
export TMPDIR="$HOME/tmp"
export SSL_CERT_FILE="$HOME/usr/local/ssl/cert.pem"
# ⚠ CONAN_HOME **必须纯 ASCII**（见问题 #9：中文路径会让 toybox sed 在 config.status 的
#   分隔符自检里恒失配 ⇒ `configure: error: could not make ./config.status`）
export CONAN_HOME="$HOME/tmp/ch/home-zhuli11-mednafen"
cd ~/qzy/主理-11-mednafen-1.32.1
python3 scripts/ohc-run.py conan-verify mednafen 1.32.1     # G0/G1/G2（含真 conan create）
python3 scripts/ohc-run.py finish mednafen 1.32.1 built     # W2 结构 + R36 + W3 本地 CI
```

配方内实际执行的序列（`conanfile.py build()`）：`apply_conandata_patches` →
`autotools.configure()` → `autotools.make()` → `autotools.make(target="check")`。
`generate()` 做两件事：`PkgConfigDeps(self).generate()` + 把 `generators_folder` 挂进
`PKG_CONFIG_PATH`（`tc.configure_args.append("PKG_CONFIG_PATH="+self.generators_folder)`），
以及把 `TMPDIR/TMP/TEMP` 钉到 `build_folder/.hmdfs-tmp`（OHOS `/tmp` 是只读 erofs）。

原生 driver 路径（14 步）另有一条链，实测命令与读数：

```bash
sh 经验文档/tools/build-slot.sh --mem 4000 --jobs 4 --wait 1800 -- bash -c \
  "cd <worktree> && export CC=clang CXX=clang++ AR=llvm-ar RANLIB=llvm-ranlib \
   NM=llvm-nm STRIP=llvm-strip && CONAN_HOME=… timeout 10800 \
   python3 scripts/ohc-run.py build mednafen 1.32.1"
```

driver step3 的原生 `sh configure` 需要 `PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig`
下有 `sdl2.pc` / `flac.pc`；本机 `~/usr/local` 原本两者皆缺（`pkg-config --exists` 全 NO），
已按仓内既有机制（driver 自己 `auto_install_tool` 用的同一条 cmd-pkgs 通道，直连
`releases/download/pkgs/install.sh`）装入 `SDL2 2.30.0` 与 `flac 1.4.3` 预编译包。
⚠ 注意：**原生路线用的是 cmd-pkgs 的 SDL2 2.30.0 / flac 1.4.3，conan 路线用的是
conan 的 sdl2/2.30.10 / flac/1.5.0**，两者启动横幅版本串不同（见「验证结果」）。

## 遇到的问题与解决方案

| # | 症状（首条真实错误原文） | 根因 | 解决方案 |
|---|---|---|---|
| 1 | `configure:3387: error: no acceptable C compiler found in $PATH` | OHOS 只有 `clang`，PATH 里没有 `cc`/`gcc`；`AC_PROG_CC` 顺序探 gcc→cc→cl.exe 全灭 | 原生 driver 前 export `CC=clang CXX=clang++ AR=llvm-ar RANLIB=llvm-ranlib NM=llvm-nm STRIP=llvm-strip`（知识库 **E001**）。**CI 侧由 conan 的 AutotoolsToolchain 从 profile 注入 CC/CXX，配方里不硬写 CC**（R33） |
| 2 | `configure:4418: error: cannot guess build type; you must specify one`；`sh config.guess` 自报 `version 2018-02-24` 且输出 `unable to guess system type`；`sh config.sub aarch64-unknown-linux-ohos` → `machine 'aarch64-unknown-linux' not recognized` | 随包 config.guess/config.sub 是 2018 年版，不认真机 `uname -s = HarmonyOS`（`uname -m = aarch64`、`uname -r = HongMeng Kernel 1.12.0`） | 最小补丁 `0001-config.guess.patch`（+11 行，插 `*:HarmonyOS:*:*` 分支输出 `aarch64-unknown-linux-ohos`）+ `0002-config.sub.patch`（+2/-2 行，maybe_os 与 OS 白名单接受 `linux-ohos`）。**不整文件替换、不传 --build/--host**（E007/E1092/E072 口径）。实测补丁后：`sh config.guess` → `aarch64-unknown-linux-ohos`，`sh config.sub $(sh config.guess)` → 同值 |
| 3 | `./config.status[986]: can't create ./confejauNK/subs1.awk: Permission denied` / `config.status: error: could not setup config files machinery` | HMDFS 上 `umask 077 && mktemp -d ./confXXXXXX` 建出的目录是 `drwx--S---`，owner 自己也写不进去（**E114**） | `0003-configure.patch` 第 1 段：configure 内嵌 config.status 模板两处 `umask 077` → `umask 022`（仓内 1152 个包同款最小修法；实测同 umask 下 `mktemp -d` 产 `drwxrws--x` 且可写） |
| 4 | `src/drivers/Joystick_Linux.cpp:498: use of undeclared identifier 'versionsort'`（三处：498 / 559 / 560） | OHOS 的 musl 系 `<dirent.h>` 不声明 GNU `versionsort(3)`（整棵 sysroot include 树 grep 命中 0；编译行已带 `-D_GNU_SOURCE` 仍报）（**E1574** 同族） | `0005-src-drivers-Joystick_Linux.cpp.patch`：`#ifdef __OHOS__ #define versionsort alphasort #endif`。**披露**：枚举集合由 `evdev_filter`/`jsdev_filter` 决定，比较器只决定列出次序 ⇒ 设备可用性不变、排序语义降级为字典序（`/dev/input` 下 `event2`/`event10` 混排时次序与上游不同） |
| 5 | `intl/lock.h:150: error: use of undeclared identifier 'pthread_cancel'`（`gnulib glthread pthread_in_use()` 探测） | gnulib 用 `#pragma weak pthread_cancel` + `(pthread_cancel != NULL)` 探测线程库；OHOS sysroot 的 `pthread.h` 没有该符号（pre-scan 的 **PSCAN-MUSL-001** 命中） | `0004-intl-lock.h.patch`：探测符号改用已声明的 `pthread_self`（`#ifndef pthread_self #pragma weak pthread_self` 上游本来就有） |
| 6 | `ld.lld: error: libtrio.a(libtrio_a-trio.o):(function trio_printf: .text+0x64): improper alignment for relocation R_AARCH64_LDST64_ABS_LO12_NC: 0x57A1E3C is not aligned to 8 bytes`（13 条，全部指向**同一个**地址） | 上游 configure 强制 `-fno-pic -fno-pie -fno-PIC -fno-PIE` + `-no-pie`。非 PIC 目标文件对 libc **数据**符号（`llvm-objdump -r drivers/main.o \| grep LDST64` 实见 `R_AARCH64_LDST64_ABS_LO12_NC stdout`）产生「按 8 字节对齐取址」的重定位，而 copy relocation 落点只有 4 字节对齐 ⇒ ld.lld 直接失败。**3 行最小复现**：`fprintf(stdout,…)` 加 `-fno-pic -fno-pie -no-pie` 链接即复现（同一条 error），去掉这组开关即通过（本机 clang 15 实测） | `0003-configure.patch` 第 2 段：在 NOPICPIE 那段落前插 `case $host in *-ohos*) NOPICPIE_FLAGS=""; NOPICPIE_LDFLAGS="";; esac`，**OHOS 上保留 SDK 的 PIE/PIC 默认值**，其他平台行为不变。同族已合入先例：`archives/d/demumble/1.3.0/patches/0001-ohos-keep-pie-on-aarch64.patch`（CMake 侧同款处置）。实测 patch 后 `src/Makefile` 的 `AM_CFLAGS/AM_CXXFLAGS/AM_LDFLAGS` 只剩 `-fjump-tables -mno-retpoline`（后者 clang 未支持，仅一条 warning） |
| 7 | `make: jobserver mkfifo: …/GMfifoNNNNN: Operation not permitted` | HMDFS 不允许 mkfifo，make 的 jobserver FIFO 建不出来 | **仅 warning**，make 继续按 -jN 跑（本机实测两次全量构建均在只带这行 warning 的情况下跑到 `MAKE_RC=0`），无需处置 |
| 8 | driver step3 报 `❌ configure failed (RC=1)`（0 秒） | 我把 `PKG_CONFIG_PATH=<generators_folder>` 写进了 `manifest.yaml` 的 `configure_options`，而 `scripts/ohc/driver.py::_read_extra_args()` 会把它逐条拼进 **原生** `sh configure` 命令行（不做引号保护）⇒ `<`/`>` 被 shell 当重定向 ⇒ `ambiguous redirect`，configure 立刻退出 1 | 该字段改回 `[]`（PKG_CONFIG_PATH 由配方 `generate()` 注入）。同时 driver 依据知识库 **E521** 自动重试了 `autoreconf -fi`，实测**没有**改坏源树（config.guess/config.sub/configure 的 mtime 与内容仍是补丁后版本），但它的 `do_retry` 会在 vpath 目录跑 `make distclean` ⇒ 把已编译的 .o 清空（下一轮要全量重编） |

| 9 | conan 路线的 `configure` 走到 `configure: creating ./config.status` 后报 `configure: error: could not make ./config.status`（`sh -x` 追到 autoconf 的 delimiter 自检循环：`ac_delim_n=300` 恒 ≠ `ac_delim_num=304`，5 轮后落到 `as_fn_error`） | **CONAN_HOME 含中文**（`~/tmp/ch/home-主理-11-mednafen`）⇒ conan 生成的 `.pc` 里的 prefix 带非 ASCII 字节，`FLAC_CFLAGS/FLAC_LIBS` 等进入 `ac_subst_vars`；设备 `/usr/bin/sed` 是 **toybox 0.8.12**，它对含多字节字符的超长行整行失配（`sed -n "s/.*$ac_delim\$/X/p"` 少数 4 行）。仓内同款已记录先例：`archives/r/rgb/1.1.1/notes.md` §3.4、`archives/e/exfatprogs/1.4.3/notes.md` #2、`archives/f/fslsfonts/1.0.7/notes.md` #3（结论一致：**配方侧无需改动，CI 的 conan home 本就是 ASCII**） | 新建**纯 ASCII** CONAN_HOME `~/tmp/ch/home-zhuli11-mednafen`，按派发卡三步播种（拷 `remotes.json`/`settings.yml`/`global.conf`/`version.txt`/`extensions` → 写 `global.conf` → `conan remote list` 自检出现 `ohpcd`）。换 home 后同一配方**直接越过** config.status 那一关 |
| 10 | conan `make` 首错 `src/drivers/main.h:11:10: fatal error: 'SDL.h' file not found`（main.o/ers.o/help.o 三处） | SDL2 头装在 `<sdl2 package>/include/SDL2/` 下，上游却写 `#include <SDL.h>`；conan 的 `PkgConfigDeps` 按 `cpp_info.includedirs` 生成的 `sdl2.pc` 只有 `Cflags: -I<pkg>/include`（SDL2 官方 `sdl2.pc` 是 `-I${includedir}/SDL2`）⇒ configure 的 `checking for SDL... yes` 照样过、`make` 才炸。同族先例：`archives/e/exfatprogs/1.4.3` 的 blkid 子目录缺失 | 配方 `generate()` 把依赖图里的 `-I<sdl2 package>/include/SDL2` 追加进 `tc.extra_cflags`/`extra_cxxflags`（R33/R49：路径来自 conan 依赖图） |
| 11 | 修好 SDL 后 `make` 下一处首错 `src/drivers/main.cpp:1802:11: fatal error: 'FLAC/all.h' file not found` | 上游只在 `src/Makefile.am:2` 写了 `DEFS = @DEFS@ @FLAC_CFLAGS@`，而 **drivers 子目录自己的** `src/drivers/Makefile.am:2` 是 `DEFS = -DLOCALEDIR=... @DEFS@ @SDL_CFLAGS@` —— **漏了 `@FLAC_CFLAGS@`**；在"flac 装在系统默认 include 路径"的机器上不可见，conan 把它装在私有 prefix 才暴露。实测 conan 侧 `src/drivers/Makefile:283` 的 DEFS 里确实没有 flac include，而 `src/Makefile:1543` 有 | 同一处把 `-I<flac package>/include` 也追加进 `extra_cflags`/`extra_cxxflags`（不 patch 上游 Makefile.am，避免为一个环境差异改上游构建文件） |
| 12 | 修好 FLAC 后 `make` 首错 `src/snes_faust/ppu_render_common.inc:1221: error: ISO C++17 does not allow 'register' storage class specifier [-Wregister]`（6 处） | 上游 `configure.ac:31` 自己把 CXX 定成 `-std=gnu++11`，但 conan profile `ci/conan/profiles/ohos-aarch64` 的 `compiler.cppstd=17` 会让 `AutotoolsToolchain` 往 CXXFLAGS 再塞 `-std=gnu++17`，而 CXXFLAGS 在 configure 追加的 `-std` **之后** ⇒ 实际生效 17（C++17 已删除 `register`）。原生 driver 构建没有 conan 的 `-std`，故不暴露 | 配方把标准按上游声明的级别钉回 `-std=gnu++11`（`tc.extra_cxxflags`，落在 CXXFLAGS 末尾覆盖 toolchain 注入值）；实测 conan 侧编译行已变成 `clang++ -std=gnu++11` |
| 13 | `finish`/`conan-verify` 都在 step [9/14] 之后覆盖配方 | `scripts/ohc/driver.py::_step9_conan_recipe()` 调 `conan_init(..., force=True)`，**无条件**重写 `conanfile.py` / `conandata.yml` / `test_package/{conanfile.py,MANIFEST.yml,test.c,CMakeLists.txt}`（`test.sh` 因不在模板清单里而幸存）。实测该轮把 recipe 换回 autotools 空模板 ⇒ 后续 G2 报 `*** libflac >= 1.3.0 not found!`（因为模板没有 `PkgConfigDeps`/`PKG_CONFIG_PATH`），且 `conandata.yml` 的 `strip: 1` 被抹掉 | 手写交付物已按原文恢复，并在 `conandata.yml` 头部写明"交付前禁止再跑 `build` 的 Step9 及以后"；验证只走 `conan-verify` + `finish`（两者都不调 conan-init）。**只报告不擅改框架**（`scripts/` 无提交通道） |
| 14 | G2 的 `conan create` 偶发 `Package 'zlib/1.3.1.1' not resolved: … SSLError(SSLEOFError(8, '[SSL: UNEXPECTED_EOF_WHILE_READING…`（对 `conan.cnb.cool` 的 `/v1/ping`） | 制品仓 HTTPS 与 gitcode 同源的**间歇 SSL 抖动** | 预热依赖（`conan download <精确引用> -r=ohpcd`，逐个 5–6 次重试）后再跑；本包 4 个依赖（zlib/sdl2/flac/libogg）按此全部落进 ASCII home 缓存 |

## 上游测试（五维账本，提交前四向核对）

**结论先说**：mednafen **没有**把任何测试注册进构建系统——顶层
`Makefile.am` 只有 `SUBDIRS = po intl src`，全树 grep 无 `TESTS` / `check_PROGRAMS` /
`add_test`，所以 `make check` 是**0 用例空跑**（配方里仍保留这一步，是为了与 CI L1c 的
「build() 中真跑 make check」口径一致）。真正的上游断言有**两处注册入口**，
且都是「编进二进制、运行时执行」：

| 维度 | 数 | 来源与读法 |
|---|---|---|
| `N_static`（资产口径） | **103** | 60 + 12 + 31（见下三行） |
| 上游·单元（内置断言注册入口） | **60** | `src/tests.cpp` 的 `MDFN_RunCheapTests()` 函数体逐条调用语句（`grep -c` 实点：位运算/有符号溢出/结构体对齐/浮点/`md5_test`/`sha1_test`/`sha256_test`/`crc_test`/`zlib_test`/`memops_test`/`Time_Test`/`TestCDUtility`/`TestPathManip`… 共 60 条） |
| 上游·集成（扩展断言注册入口） | **12** | `src/testsexp.cpp` 的 `MDFNI_RunExpensiveTests()` 函数体逐条调用（`TestRandInit`/`TestSurface`/`TestMemoryStream`/`TestStreamMisc`/`Testsnhex`/`TestSettings`/`NVFSTest`/`Stream64Test`/`StreamBufTest`/`TestZLInflate`/`MDFN_RunExceptionTests(1,0)`/`MDFN_RunExceptionTests(4,30000)`） |
| 上游·其他（`tests/` 目录资产） | **31** | `find tests -type f \| wc -l` 实测 31：`apple2/`10（`bintodsk.cpp`、`gencrctab.cpp`、`crc.inc`、`crctab-*.bin`×8、`decimal/{decimal.asm,decimal.bin,decimal.dsk}`）+ `pce/`9（`decimal/{adc.asm,adc.pce,sbc.asm,sbc.pce,XXc.inc,gen-results.cpp,make.sh,clean.sh}`、`vcectdump/{make.sh,vcectdump.asm,vcectdump.pce}`、`font.bin`）+ `psx/`4（`gpuprec.exe`/`linefuzz.exe`/`multires-newgpu.exe`/`triorder.exe`）。**这些是人工回归语料与宿主工具，上游没有任何自动化入口**（无 Makefile、无 runner） |
| `N_registered`（构建系统注册） | **0** | 见上：`make check` 空跑 |
| `N_executed`（本次真跑） | **72** | 60 条随 `--help` 路径真跑（`MDFNI_Init()` 里无条件调用）+ 12 条随 `-exptests <dir>` 真跑；本机实测 72/72 全过（任何一条失败都会抛异常，走不到后面的输出） |
| 未执行/未覆盖 | **31** | 上表 `tests/` 目录的 31 个资产：28 个是「要人工跑模拟器 + 比对生成结果」的语料（`.pce`/`.dsk`/`.bin`/`.exe`），4 个 PSX `.exe` 还需 PS1 BIOS；3 个宿主工具（`bintodsk.cpp`/`gencrctab.cpp`/`gen-results.cpp`）本身不是测试、也没有构建入口。逐项技术原因写在 PR 补充说明 |
| `N_consumer`（新增消费者测试） | **1** | `test_package/test.sh`（1 个程序 / **21 条断言**） |
| `N_assertion` | **21** | `test_package/test.sh` 内 `run_help`/`run`/`grep_check`/`grep_absent`/`file_check` 调用行数；由 `test_package/conanfile.py::_count_assertions()` 现数，与 `HMBS_TEST_PACKAGE_RESULT.discovered` 同源 |

**适配后合计 = 73**（72 执行 + 1 消费者程序），**上游合计 = 103**（资产口径）；
`73 < 103` 的口径差按 `手册/04 §11.2` 的「测试数量变化原因」小节豁免（该小节写在
PR 的 `## 补充说明` 内，**不另立 H2**，因为 `pr_body_lint` 把同名 H2 列为禁止章节）。

## 验证结果（逐条读数）

**A. 原生 driver 路线（cmd-pkgs SDL2 2.30.0 / flac 1.4.3）**

```text
$ ~/tmp/builds/mednafen-1.32.1-build/src/mednafen --help
Starting Mednafen 1.32.1
 Build information:
   Compiled with gcc Clang 15.0.4 (/srv/workspace/llvm-release/2026_0313_llvm15_release/toolchain/llvm-project/clang 0e01a01d567b9acfce8edfdadb66a7b69f088fb0)
   Compiled against zlib 1.3.1, running with zlib 1.3.1(flags=0x000000a9)
   Compiled against SDL 2.30.0(SDL-release-2.30.0-0-g859844eae), running with SDL 2.30.0(...)
   Running with libFLAC 1.4.3
 Base directory: <MEDNAFEN_HOME>
 Emulation modules: apple2 nes snes gb gba pce lynx md pcfx ngp psx ss ssfplay vb wswan sms gg sasplay snes_faust pce_fast demo cdplay
Usage: <argv0> [OPTION]... [FILE]

Options:
 -help
	Show help!
…（略）
exit code = 255（**不是 0**：`--help` 命中 main.cpp:974-986 的 `return false`，
main.cpp:2408-2414 对该分支 `return -1`）
```

`make-probe4.log` 结尾：`MAKE_RC=0`（1197 条编译命令，0 条 `error:`）；
`~/tmp/builds/mednafen-1.32.1-build/src/mednafen` 82311744 B。

`test_package/test.sh` 在本机原生二进制上的实跑（只把二进制放进 PATH）：

```text
== 消费者测试汇总：21 项断言，失败 2 项 ==
  两项失败 = [5]/[6] 的依赖版本串断言，因为**原生路线链接的是 cmd-pkgs 的
  SDL2 2.30.0 / libFLAC 1.4.3**，而断言写的是 conan 依赖图的 2.30.10 / 1.5.0。
  其余 19 项全过（含 -exptests 的 12 项、cfgtest.cfg / streamtest.bin 落盘、
  无参数与非法选项两条负控制）。
```

**B. conan 路线（sdl2/2.30.10、flac/1.5.0、zlib/1.3.1.1）**

见 `reports/conan-verify-report.md`、`reports/conan-create.log`（G2 的完整
`conan create` 日志，含 test_package 的 21 项断言原文）与
`reports/w3-local-ci.log`（`ci/conan/build_and_test.sh` 的本地 CI 模拟）。
三处读数与本节数字同源；`finish` 另把 W3 结果写进 `.ci-result.json`（带日志 sha256）。

## 源码修改（patches/，逐个一句话）

| 补丁 | 行数 | 改什么 |
|---|---|---|
| `0001-config.guess.patch` | +11/-0 | 插 `*:HarmonyOS:*:*` 分支，按 `uname -m` 映射后输出 `aarch64-unknown-linux-ohos` |
| `0002-config.sub.patch` | +2/-2 | `maybe_os` 白名单与 OS 白名单接受 `linux-ohos`（否则三元组被判 invalid） |
| `0003-configure.patch` | +19/-2 | (a) config.status 临时目录 `umask 077→022`；(b) OHOS 主机不再强制非 PIC/非 PIE |
| `0004-intl-lock.h.patch` | +2/-2 | gnulib `pthread_in_use()` 探测符号 `pthread_cancel`→`pthread_self` |
| `0005-src-drivers-Joystick_Linux.cpp.patch` | +11/-0 | OHOS 下 `scandir` 比较器 `versionsort`→`alphasort` |

合计 +45/-6 行（5 个文件），**无整文件替换**；`patch -p1` 在 pristine 树上逐个
`--dry-run` 与实打都通过（本机在 `~/tmp/uc2/mednafen-1.32.1/patchtest2` 用 orig 目录
副本实测），且打完后 `sh config.guess` = `aarch64-unknown-linux-ohos`、
`grep -c "umask 022" configure` = 2、`grep -c "pthread_self != NULL" intl/lock.h` = 1、
`grep -c "define versionsort alphasort" src/drivers/Joystick_Linux.cpp` = 1。
每次改源文件后都跑了 `ohc-run.py track-edit add mednafen 1.32.1 <文件>`（R6），
`.edit-tracker.json.edited` 实测 = `[config.guess, config.sub, configure,
intl/lock.h, src/drivers/Joystick_Linux.cpp]`。

## 注意事项 / 已知限制

1. **NLS 走随包 `intl/`**（`AM_GNU_GETTEXT` 实测判定 `where the gettext function
   comes from... included intl directory`，因为 musl libc 无 `libintl`）；`--disable-nls`
   **没有**被使用，翻译面保留。
2. **ALSA / JACK = undef**（OHOS 无这两个后端）；音频走 SDL2 + OSS（`sys/soundcard.h`
   实测 yes）。GUI/声音后端能用就开，不能用如实披露。
3. **`versionsort→alphasort`** 的次序语义降级（见问题 #4 的披露）。
4. 原生 driver 的第 7 步 `make check` 在**源码目录**执行（VPATH 构建下源码目录没有
   Makefile）⇒ 必然报 `No targets specified and no makefile found`。这一步在 driver 里
   是**非阻塞**的（`_step7_check` 只在 rc≠0 时打 CHECKPOINT 并继续），但它会把
   `reports/test-report.md` 写成 `Status: FAIL`；`reports/test-report.md` 已由本轮
   **真实测试读数**重写（上游 72/72 执行、消费者 21/21），与正文/notes/manifest 同源。
5. 依赖版本串：见「编译步骤」末尾那条 ⚠（原生路线与 conan 路线的 SDL2/flac 版本不同）。
6. `finish` 的 step5b `check_knowledge_gap` 判红是**存量现象**（`手册/04 §11.5`：
   全仓 4997 个有 `knowledge_gained` 的包里 4623 个同为红，本包 `knowledge_gained`
   已逐条带 `ref:` 字样），未改 manifest 去凑；按 §11.5 在 PR 的
   「未执行/未覆盖的检查」里一句话披露。
---

**编译结束**: 2026-10-19 05:47
**最终状态**: built
