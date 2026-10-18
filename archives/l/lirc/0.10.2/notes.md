# lirc 0.10.2 适配笔记（HarmonyOS PC / aarch64）

## 1. 源码与版本核对（W0）

| 判据 | 读数 | 取数命令 |
|---|---|---|
| 上游 tag | `lirc-0.10.2` = `2650b422f4111a6b9abdf3bc85ff4711bd735e3d` | `git -C <clone> log -1 --format='%H %d'` |
| 官方发布物 | `lirc-0.10.2.tar.bz2`，2418298 B | `stat -c '%s'` |
| sha256 | `3d44ec8274881cf262f160805641f0827ffcc20ade0d85e7e6f3b90e0d3d222a` | `sha256sum` |
| 源 URL | `https://downloads.sourceforge.net/project/lirc/LIRC/0.10.2/lirc-0.10.2.tar.bz2` | 重新下载后 sha256 与上表一致 |
| 硬依赖 | 无。`libusb`/`libftdi`/`portaudio`/`ALSA`/`systemd`/`libudev` 全部为可选，探测不到即关闭对应驱动/插件 | `configure.ac` 的 `PKG_CHECK_MODULES`/`AC_CHECK_LIB` |
| 可移植性 | 无 ISA 专属头（无 `altivec.h`/`mmx`/`3dnow`）、无 `register_printf_*` glibc 钩子族 | `grep -rE 'altivec\.h|mmx|3dnow|register_printf' <src>` → 0 命中 |
| 制品仓重复检测 | `conan list -r=ohpcd "lirc*"` = 0 命中 | 平台侧同步核对 |

上游 release tarball **不含 `test/` 目录**（`make dist` 的 `EXTRA_DIST` 未收录该
子树），因此 CppUnit 上游测试只能取自 git tag。本配方把 tag 的 `test/` 树逐字
复制到 `upstream-tests/`，见 §3。

## 2. 上游测试 N 的清点（N = 35）

上游测试框架是 CppUnit，`test/run-tests.cpp` 注册 6 个 suite，suite 内用
`ADD_TEST("name", func)` 宏逐条注册用例（宏在各 suite 头文件里自定义为
`TestSuite::addTest`）：

```sh
git clone --depth 1 --branch lirc-0.10.2 https://git.code.sf.net/p/lirc/git
grep -rn 'ADD_TEST(' <clone>/test/*.h | grep -v '# *\(define\|undef\|ifdef\|ifndef\)' | wc -l
# 35
```

| suite | 头文件 | 注册用例数 |
|---|---|---|
| ClientTest | `test/ClientTest.h` | 9 |
| DecodeTest | `test/DecodeTest.h` | 8 |
| DrvAdminTest | `test/DrvAdminTest.h` | 3 |
| IrRemoteTest | `test/IrRemoteTest.h` | 9 |
| LogTest | `test/LogTest.h` | 3 |
| OptionsTest | `test/OptionsTest.h` | 3 |
| **合计** | | **35** |

四种口径（源码宏数 / 框架注册数 / assertion 数 / 消费者断言数）中，本包采用
**框架注册数**；`CPPUNIT_TEST` 宏数为 0（上游不用它），`CPPUNIT_ASSERT` 数明显
大于 35（每个用例多条断言），不作为 N。候选数法取最大值 = 35。

> 上游缺陷（不影响计数，但影响判读）：`test/DecodeTest.h:32-39` 把
> `testSpaceEnc2/3`、`testRc5`、`testRc6`、`testRaw` 全部注册到同一个 C++
> 函数 `testSpaceEnc1`，因此运行期只会驱动 `tests/space-enc-1/run-test.sh`；
> 且 8 个用例都不检查 `system()` 的返回值。8 个脚本的独立执行结果见 §4.3。

## 3. `upstream-tests/` 的来源与差异

`upstream-tests/` = git tag `lirc-0.10.2` 的 `test/` 树，**逐字节一致**，仅两处
例外（均已在 PR 正文声明）：

| 差异 | 原因 |
|---|---|
| 未收录 `testdata.tar.gz`（218004 B） | 它是压缩归档，入库会撞「禁止提交归档」门禁；且 CppUnit 套件无任何代码引用它（`grep -rn testdata test/` 只命中 `.gitignore`） |
| 未收录 `lirc -> ..` 符号链接 | 指向目录树之外的相对符号链接；`build()` 运行时按上游语义重建 |

**文件模式**：上游 `test/` 里 11 个脚本/工具是 `100755`（`find-reps.bash`、
`lirc-codecs-regression-test.sh`、8 个 `tests/*/run-test.sh`、`tests/rc5/find_reps`），
本仓库同样以 `100755` 入库——**HMDFS 上 `chmod +x` 无法持久化**（设备所有文件都是 770，
且新 worktree 预设 `core.fileMode=false`，`git add` 一律记 100644），因此这 11 条是用
`git update-index --chmod=+x` 单独写入索引的（notes/device-facts.md §一.27）。这一步是
必要的：在保留文件模式的检出（如 CI worker 的正常文件系统）上，644 的
`./run-test.sh` 会 `rc=126 Permission denied`，§4.3 的脚本层读数将无法复现。

逐字节一致性核验（逐文件 `sha256` 比对，排除上述两项）：61/61 文件哈希相同。

## 4. OHOS 适配要点

### 4.1 编译期

| # | 现象（原始报错） | 根因 | 处置 |
|---|---|---|---|
| 1 | `configure: error: cannot guess build type` / `config.sub ... OS 'ohos' not recognized` | tarball 内 `config.sub`（2022-01-03）/`config.guess`（2022-05-25）是 2022 年版，不认 `aarch64-*-ohos`；且 `config.guess` 在 HMDFS 临时目录里跑不起来（`can't create .../dummy.c: Permission denied`） | `build()` 里用 `automake/1.18` 提供的现代 `config.sub`/`config.guess`（2024-05-27/2024-07-27）替换，并显式传 `--build/--host=aarch64-unknown-linux-ohos`（绕开 `config.guess`） |
| 2 | `config.status: error: could not setup config files machinery` / `can't create ./confXXXXXX/subs1.awk: Permission denied` | `configure` 用 `(umask 077 && mktemp -d)` 建私有临时目录；HMDFS 上目录模式保留 setgid 位落成 2700，owner 随后被拒写 | `build()` 中把 `umask 077 && mktemp -d` 归一为 `umask 022 && mktemp -d` |
| 3 | `../version:1:1: error: a type specifier is required` + libc++ `new:192: no type named 'size_t'` | 构建根目录的生成文件 `VERSION` 在**大小写不敏感**文件系统上顶替了 libc++ 的 C++20 `<version>` 头（`cstddef` 无条件 `#include <version>`）；automake 的 `DEFAULT_INCLUDES = -I. -I$(top_builddir)` 让 `..` 先于系统头 | ① 删掉源树里 tarball 自带的 `VERSION`；② `make` 传 `DEFAULT_INCLUDES='-I. -idirafter ..'`（构建目录的 `VERSION` 仍在，但让位于系统头；`config.h`/`paths.h` 仍可解析） |
| 4 | `lib/drv_enum.c:…: error: incompatible integer to pointer conversion`（`udev_device`/`usb_busses`/`get_sysattr` 一片报错）+ `warning: 'SH_PATH' macro redefined` | **tarball 里带了一份发行机生成的 `lib/lirc/config.h`**（定义了 `HAVE_LIBUDEV_H`/`HAVE_USB_H`/`HAVE_LINUX_DEVINPUT`/`HAVE_SOUNDCARD`，本平台都没有）。`lib/lirc/curl_poll.h:35` 写的是 `#include "config.h"`，引号包含先从**包含者所在目录**找 → out-of-tree 构建下永远命中这份陈旧副本，压过构建目录里新生成的 config.h。上游自己的 `BUILT_SOURCES` 规则 `lirc/config.h: ../config.h` 只在 in-tree 下"顺手"覆盖它 | `build()` 里删除源树的 `lib/lirc/config.h`，让 make 在构建目录重新生成并生效 |
| 5 | `error: ISO C++17 does not allow 'register' storage class specifier [-Wregister]`（`daemons/lircd.cpp:320`、`daemons/lircrcd.cpp:145`） | conan profile 固定 `compiler.cppstd=17`，C++17 移除了 `register`，clang 15 下升级为硬错误 | 补丁删掉这两个 `register`（无语义影响） |
| 6 | `ld.lld: error: undefined reference due to --no-allow-shlib-undefined: rindex`（链接 `lircrcd`） | musl 不提供 `rindex(3)`（glibc 遗留），`lib/lirc_client.c:1822` 在用 | 补丁改 `strrchr()`（POSIX 等价） |
| 7 | `mplay.c:200: incompatible integer to pointer conversion initializing 'pthread_t'` | musl 的 `pthread_t` 是指针，`= -1` 哨兵不成立 | 补丁改为 `0` 哨兵（三处） |
| 8 | `call to undeclared function 'pthread_cancel'` ×3（atwf83/zotac/mplay） | OHOS sysroot 的 `<pthread.h>` **未声明** `pthread_cancel`，但运行时 libc **导出**该符号（`llvm-nm -D /system/lib64/libc.so` → `T pthread_cancel`；sysroot 的 stub `libc.so` 里没有） | 补丁在三个插件里补显式原型，消除隐式声明 |
| 9 | `cp: python-pkg/VERSION: No such file or directory` + `make: *** [Makefile:1641: python-pkg/VERSION] Error 1`（间歇复现） | out-of-tree 构建的 `-j>1` 竞态：`BUILT_SOURCES` 里 `python-pkg/VERSION` 的规则是 `cp $? $@`，而它要写进去的目录由另一条 `BUILT_SOURCES` 规则 `$(abs_builddir)/python-pkg/setup.py` → `cp -ar $(top_srcdir)/python-pkg $(abs_builddir)` 创建；两者并行时前者可能先跑 | `build()` 里先串行 `make -j1 python-pkg/lirc/config.py`（该目标的依赖链会建好 `python-pkg/`），再用 `-j4` 跑其余 |
| 10 | `warning: call to undeclared function 'major'; ISO C99 and later do not support implicit function declarations`（`plugins/default.c:375`）+ 运行期 `Error relocating …/plugins/default.so: major: symbol not found` | `plugins/default.c` 调 `major(s.st_rdev)` 却只 `#include <sys/types.h>`。glibc ≥ 2.28 与 **OHOS/musl sysroot 都不再经 `<sys/types.h>` 引出 `sys/sysmacros.h` 的 `major()/minor()` 宏**（该头存在于 sysroot 且含 `#define major(x)`，只是没被包含）⇒ 隐式声明 + 未定义符号；共享库允许未定义符号所以**链接照过**，但 `.so` 在运行期无法加载 | 补丁里给 `plugins/default.c` 加 `#include <sys/sysmacros.h>`（glibc/musl 都有，无需 `__OHOS__`，符合 R8） |

> 第 10 条是 **W4 第 4 轮审计（1c2f64db）发现的 P1**：本平台 30 个插件里 `default.so` 是唯一
> 一个装好即不可加载的。逐条复核读数：构建日志第 859 行有该告警；配方自己的 `lirc-lsplugins`
> 第 2431-2432 行把 `default.so` 标 `F--` 并打印 `# Error: Error relocating … major: symbol not found`；
> 对安装后 30 个 `.so` 逐个 `ctypes.CDLL` 实测 **1/30 失败**（`default.so`），`llvm-nm` 显示
> 只有它带未定义 `major`，而 musl 的 `/system/lib64/libc.so` 不导出 `major`。功能影响有限
> （本平台无 `/dev/input`，default 驱动的 devinput 面本就不可用），但「插件目录可加载」这一
> 验证声明在修复前**不成立**——见 §5 对 `test_package` 断言的加固。

补丁文件：`patches/0001-portability-musl-ohos-cxx17.patch`（7 个源文件，纯可移植
性修改，无 `__OHOS__` 宏、无平台分支）。

### 4.2 配置探测结果（本机真实能力）

```
x_progs:                  (none)      → BUILD_XTOOLS=no（无 X11）
ENABLE_UINPUT:            no          （/dev/uinput 不存在）
HAVE_DEVINPUT:            no          （/dev/input 不存在）
LINUX_KERNEL:             yes         （clang 定义 __linux__）
BUILD_HIDDEV/I2CUSER/DSP: yes / yes / yes
BUILD_USB/FTDI/LIBALSA/LIBPORTAUDIO/ALSA_SB_RC: no（依赖不可得，非止损）
HAVE_PYTHON35:            no          （无 python-X.Ym pkg-config，python 客户端不构建）
```

`make check` 说明：上游 tarball 的 `Makefile.in` 里**没有任何 `TESTS`/`check_PROGRAMS`**，
`make check` 是空目标，上游的自动化测试实际入口是 git 里的 `test/` 树（`./run-tests`），
本配方按同一语义在 `build()` 中编译并运行它。

### 4.3 上游测试执行

执行方式：`build()` 中把 `upstream-tests/` 复制到 `<build>/test`，用 clang++ 按
上游 `test/Makefile` 的同名规则编译 `run-tests`（上游规则里硬编码 `gcc`，本平台
只有 clang++），然后在 `test/` 目录下运行 `./run-tests`，输出经 `tee` 同时进
`conan create` 日志与 `upstream-cppunit.log`。上游 8 个脚本的 `#!/bin/bash` 在
OHOS 上不存在（无 `/bin/bash`），运行前把解释器路径归一为
`/data/service/hnp/bin/bash`（**仅解释器路径，测试逻辑零改动**）；
`lirc-codecs-regression-test.sh` 保持原样——上游给它写的是坏 shebang
`#!/usr/bin/env /bash`（多一个斜杠），且它不属于 CppUnit 套件。

CppUnit 判定（`Run: 35 Failures: 11 Errors: 0`，日志见 `reports/` 副本）：

| 项 | 数 | 说明 |
|---|---|---|
| 注册/执行 | 35 | N′=35，全部执行 |
| PASS | 24 | 含 DecodeTest 8 条（见下） |
| FAIL | 11 | 9 条 ClientTest（`setUp()` 建 lircd socket 失败）+ 2 条 DrvAdminTest（硬编码计数） |
| ERROR | 0 | |
| SKIP/NOT_RUN | 0 | |

**8 个 DecodeTest 脚本的独立执行结果**（上游套件不检查 `system()` 返回值，
CppUnit 判定不反映它们，故单列）：

| 脚本 | rc | 原始证据 |
|---|---|---|
| `space-enc-1` | 1 | `var/space-enc-1.log`：`irsimsend -l decoded1 119420.conf` 产出的 `simsend.out` 为 0 字节 → `decoded2.out` 空 → `diff decoded1.out decoded2.out` 不等 |
| `DBS` | 1 | `tests/DBS/var/lircd.log`：`Error when setting driver options: "send-space:1000000\|set-infile:d9-mute.ref\|kill-on-eof:1"`；`DBS.received` 只有 `space 1000000` 一行（lircd 的 `output = var/lircd.socket` 建不起来，见下） |
| `longpress` | 1 | `var/longpress.log`：`irtestcase` 写硬编码 `/tmp/irtestcase/codes.log`，而 `/tmp` 在本设备只读 → `diff: Can't stat /tmp/irtestcase/codes.log` |
| `rc5` | 0 | `var/RC-5500.log`，`irsimreceive`/`irsimsend` 往返 + `diff` 全绿 |
| `rc6` | 1 | `var/RC1974502_00.log`：期望输出含按键重复序列（`KEY_BLUE`/`KEY_GREEN`/`KEY_RED`/`KEY_YELLOW` 各 5 条），实跑缺少这 20 行 |
| `raw` | 0 | `var/SR-90.log` |
| `space-enc-2` | 0 | `var/301_501_3100_5100_58xx_59xx.log` |
| `space-enc-3` | 0 | `var/AVR240.log` |

**11 条 FAIL 的逐条技术原因**：

1. `ClientTest` 9 条（`testReceive`/`testReadConfig`/`testReadConfig1`/
   `testReadConfig2`/`testReadConfigOnly`/`testReadConfigNew`/`testCode2Char`/
   `testSetMode`/`testGetMode`）全部在 `setUp()` 失败于
   `CPPUNIT_ASSERT(fd != -1)`；`var/client_test.log` 内为
   `Could not assign address to socketvar/lircd.socket: Operation not permitted`。
   机型实测（AF_UNIX `bind()` 探针）：`$HOME`、`$WORKSPACE_ROOT`、
   `$WORKSPACE_ROOT/tmp`、`$TASK_DIR/test-home` 全部 `EPERM(errno=1)`；`/tmp` 只读
   (`EROFS`)；**`/data/storage/el2/base`（应用私有目录）正常**；抽象命名空间
   socket 与 TCP 回环均正常。→ 平台/沙箱限制，非配方问题；lircd 无法在本工作区
   建立控制 socket。
2. `DrvAdminTest::testCount`：`count == DRIVER_COUNT`（硬编码 51）。
   实测 `LIRC_TEST_DEBUG=1` → `Driver count: 39`。差额 12 = devinput/uinput/USB/
   FTDI/portaudio/ALSA 驱动族在本平台未编译（`BUILD_*` 全 no）。
3. `DrvAdminTest::testListPlugins`：`count == PLUGIN_COUNT`（硬编码 40）。
   实测 → `Plugin count: 30`。差额 10 = 需要 libusb/libftdi/portaudio/ALSA/USB 的
   插件未构建；磁盘上 `lib/lirc/plugins/*.so` 实测 30 个。

> 未采用「把 `DRIVER_COUNT`/`PLUGIN_COUNT` 改成实测值」的改法：那等于削弱上游断言，
> 属于凑数；按环境限制逐条归因。

### 4.4 上游套件必须「有界执行」（CI 实测教训）

CI 构建 #95964（changeid 118463，PR #16304 首次触发）在 `conan build-test` 步被
**SIGTERM** 打断，日志尾部（平台只暴露 tail）：

```
lirc/0.10.2: Running the upstream CppUnit suite (35 registered cases): ./run-tests
................Could not assign address to socketvar/lircd.socket: Operation not permitted
do_connect: could not connect to socket
connect: No such file or directory
F
Signal 15
ERROR: Exiting with code: 5
Received SIGTERM!
[fail] lirc/0.10.2 — conan create failed
```

`Exiting with code: 5` / `Received SIGTERM!` 是 **conan 自己的信号处理器**打印的
（`conan/cli/cli.py:281`，`ERROR_SIGTERM = 5`），即 conan 被外部 SIGTERM 终止，而不是
配方抛异常；CI 自己的构建上限是 `timeout --signal=KILL 3600 conan create`
（`ci/conan/build_and_test.sh:1364`）——`SIGKILL` 且 3600s，与观测到的 SIGTERM/≈210s 不符，
故终止来自 worker/步级外部因素。但根因面里有**配方侧可加固的一点**：上游 CppUnit 套件
（尤其 `ClientTest::testReceive` 的 `while (code == NULL && status == 0) lirc_nextcode(...)`
与 `system(RUN_LIRCD)`）会在 AF_UNIX socket 不可用时无界阻塞，上游没有任何超时。

处置（本配方）：`./run-tests` 与 8 个 DecodeTest 脚本改为
`_run_bounded()` —— `subprocess.Popen(..., start_new_session=True)` + `wait(timeout=)`，
超时用 `os.killpg(SIGKILL)` 杀**整个进程组**（不用 toybox `timeout`：它不杀子进程树、
自身偶发不返回，见 notes/device-facts.md §一.25），上限 300s / 120s；被本界杀掉时
打印 `HMBS_UPSTREAM_TEST_RESULT={...,"status":"aborted",...}` 并**不**让构建失败
（设备上实测 ~30s 跑完，不受影响）；测试遗留的 `*.pid`（lircd/lircrcd）按 pid 回收，
不用 `pkill` 之类的名字匹配。

设备实测（同配方）：`Run: 35 Failures: 11 Errors: 0`，8 脚本 `rc5/raw/space-enc-2/space-enc-3`
pass、`space-enc-1/DBS/longpress/rc6` fail —— 与 §4.3 完全一致，有界化未改变设备读数。

### 4.5 上游套件在 CI 上「异常终止」的根因与两条处置（CI #98207）

CI 构建 #98207（changeid，PR #16304 第 4 次触发，worker CI-030）在 conan-build-test
步失败：`build()` line 169 → `_run_upstream_tests()` line 401 抛
`ConanException: upstream CppUnit summary not found in <build>/upstream-cppunit.log`，
日志尾部（逐字）：

```
................Could not assign address to socketvar/lircd.socket: Operation not permitted
do_connect: could not connect to socket
connect: No such file or directory
F
```

即套件在**第 1 个 ClientTest 失败块之后就没有再输出**，没打出 `Run: … Failures: …` 汇总。
设备侧同配方同套件完整跑完（`Run: 35 Failures: 11 Errors: 0`），设备日志里每个 ClientTest
失败块后面还有一行 `Cannot kill lircd (<pid>).: No such process`——**CI 日志里那一行没有出现**。

**根因（设备侧可复现，逐条读数见 `$TASK_DIR/repro/`）**：上游
`test/ClientTest.h` 的 `setUp()`（line 86-96）与 `tearDown()`（line 117-135）都把
`var/lircd.pid` 读进一个**从未初始化**的局部 `int pid`（`ifstream` 打开失败或文件为空时
`buffer << pidfile.rdbuf()` 会置 failbit，随后的 `buffer >> pid` 直接 no-op，值保持栈上残留），
然后调用 `kill(pid, SIGTERM)`。本平台上 lircd **永远写不出**这个文件（AF_UNIX `bind()`
EPERM，§4.3-1），因此该调用带的是**未初始化栈值**：设备实测同一二进制多次运行分别得到
`852060116`、`-657740012`、`-260616428`、`1360129684`、`-1487913196`。

- 值为**非零垃圾**时 → `kill()` 返回 `ESRCH` → 走 `else` 分支打印
  `Cannot kill lircd (N).: No such process` → 套件继续（设备上的常态，故设备能跑完）。
- 值为 **0** 时 → `kill(0, SIGTERM)` = 向**自己所在的进程组**发 SIGTERM →
  run-tests 自己在 `tearDown()` 里被 SIGTERM 杀死，`Popen.wait()` 得 `rc=-15`
  （不是配方 bound 的 `rc is None`）→ 没打汇总 → 配方按原逻辑抛异常 → `L1_RESULT=fail`。
  这与 CI 日志「停在第一个 `F`、没有 `Cannot kill lircd` 行」逐字吻合。
- 值为 **-1** 时 → `kill(-1, SIGTERM)` 会向**该用户能发信号的所有进程**发 SIGTERM——
  共享 worker 上的误杀面（比 `pkill lircd` 更大）。

复现（`$TASK_DIR/repro/`，设备侧实跑）：

```sh
# ① 常态（无 pid 文件）：跑完 35/11/0，pid 为栈垃圾（本例 -1487913196）
sh repro/run2.sh t1-baseline ./run-tests
# ② 让 `kill` 的实参落在 0 上（诊断 shim 把上游的 kill(pid,SIGTERM) 改写成 kill(0,SIGTERM)）
LD_PRELOAD=repro/forcezero.so sh repro/run2.sh r5a-ci ./run-tests
#    → 输出与 CI 尾部逐字一致（16 个点 + lircd EPERM 三行 + F），随后 CHILD_SIGNALED sig=15
# ③ 同一条件 + 本配方的隔离：完整跑完
LD_PRELOAD=repro/forcezero.so sh repro/run2.sh r7-final sh -c "trap '' TERM; exec ./run-tests"
#    → CHILD_EXIT rc=0，Run: 35  Failures: 11  Errors: 0
```

**处置 1（隔离上游误杀面）**：`./run-tests` 改为经
`SIGTERM_ISOLATION = "trap '' TERM; exec "` 启动——`_run_bounded()` 本来就用
`/bin/sh -c` 执行命令，于是**同一层 shell** 先 `trap '' TERM` 再 `exec` 套件，
SIGTERM 的忽略属性跨 `execve` 保留并由套件的子进程继承，自指的 SIGTERM 变成无害
no-op。（实测反例：若再加一层嵌套 shell，被杀的会是**外层 shell**、套件反而活着跑完，
`wait()` 仍得 `-15`——故 trap 必须装在 exec 那一层。）本配方自己的硬界仍用 `SIGKILL`
（不可忽略），真挂死的套件照旧被杀；`_stop_test_daemons()` 相应加了
SIGTERM→（1s 未退）SIGKILL 升级，避免继承 SIG_IGN 的测试守护进程残留。
设备实测隔离后读数不变（`Run: 35 Failures: 11 Errors: 0`，9 条 `Cannot kill lircd` 行照旧出现，
因为非零垃圾 pid 走的是 `ESRCH` 分支）。

**处置 2（异常终止如实记账，不假绿）**：`_run_upstream_tests()` 只在两种**有环境归因**的
形态下记 `status="aborted"` 并**不使构建失败**：①被本配方自己的 300s 硬界 SIGKILL 杀掉
（`rc is None`）；②套件死于 **SIGTERM**（`rc == -15`，即处置 1 要隔离的那条上游误杀路径，
隔离万一被绕过/被外部 SIGTERM 命中时的兜底）。两种情形都：逐字记录 `returncode` / `signal` /
partial log 路径 / `reason`，四种计数一律 `null`，另打一行
`Upstream CppUnit: ABORTED (no verdict; not counted as pass)`，**绝不写成 PASS**。
**其余一切异常退出仍是硬失败**（`ConanException`）：`rc == 0` 却无汇总、`SIGSEGV`/`SIGABRT`/
`SIGBUS`/`SIGKILL` 等信号、以及 126/127 这类 exec 失败——它们没有环境归因，崩溃或 exec 失败
**不得**藏在 `aborted` 后面（W4 第 4 轮审计把此前"任何 `rc != 0` 都记 aborted"的写法判 P2 门禁削弱，
本轮按该建议收窄）。
判读：`status=aborted` 只说明「没跑到结论」，**不能替代**设备侧的 `Run: 35 Failures: 11 Errors: 0`。

## 5. test_package（鸿蒙特有测试）`test_package/test_lirc.cpp` 链接安装后的 `liblirc_client` 并调用真实 API；
`test_package/conanfile.py` 的 `test()` 另外对安装产物做两项检查。合计 **5** 条：

| # | 断言 | 判据 |
|---|---|---|
| 1 | `lirc_readconfig_only() parses a lircrc file` | 返回值 0 且 `config != NULL` |
| 2 | `lircrc_class is parsed as 'test-lirc'` | `config->lircrc_class` 与文件里写的一致 |
| 3 | `lirc_code2char() maps KEY_POWER to 'power'` | `0000000000001bde 00 KEY_POWER test_lirc` → `"power"` |
| 4 | `packaged lircd reports version 0.10.2` | 跑安装后的 `bin/lircd --version`，断言输出含 `lircd 0.10.2`（产物自报版本指纹） |
| 5 | `lirc-lsplugins enumerated every packaged plugin with 0 load failures` | 跑安装后的 `bin/lirc-lsplugins -U <pkg>/lib/lirc/plugins -q`，断言：①**没有任何 `F--` 标记行、没有任何 `# Error:` 行**；②listing 里出现的 `.so` 路径集合 **等于** 磁盘上 `lib/lirc/plugins/*.so` 集合（30 个）；③driver 条目数 ≥20（`lirc-lsplugins` 按驱动名展开，一个 `.so` 可出多行，实测 39–41 行） |

> 第 5 条的判据在 W4 第 4 轮被加固：原实现只数行数且把 `#`/`Warning` 开头的行**滤掉**，
> 于是 `default.so` 的 `F--` + `# Error: … major: symbol not found` 恰好被滤除、40 行含 1 条
> 失败仍算通过——「插件目录可加载」这句 docstring 与实际证明力不符。加固后该断言在每个
> `conan create` 里都会**真的**验证 30/30 可加载（§4.1-10 的 P1 若复发会被当场拦下）。

注：conan 的 `AutotoolsToolchain` 会显式传 `--sbindir=${prefix}/bin`，所以
`lircd`/`lirc-lsplugins` 落在包内 `bin/`（不是 `sbin/`）。

## 6. 打包期规范化

| 项 | 现象 | 处置 |
|---|---|---|
| 构建机解释器路径泄漏 | `tools/Makefile.am:104/111` 把 `#!/usr/bin/env python3` 改写成 `#!/usr/bin/env $(PYTHON)`，安装后 6 个脚本的 shebang 变成构建机绝对路径（本机为 `/storage/Users/currentUser/usr/local/bin/python3`） | `package()` 里按正则还原为 `#!/usr/bin/env python3`，包保持可迁移 |
| `bin/lirc-data2table` 无 shebang | 上游经 `dist_bin_SCRIPTS` 把它装进 `bin/` 并置 755，但文件本身没有 shebang ⇒ 直接执行返回 `ENOEXEC`（`conan-verify` 的 L2 smoke test 因此在 `subprocess` 层抛 `OSError: [Errno 8] Exec format error` 并中断整轮） | `package()` 里为无 shebang 且含 `import ` 的脚本补 `#!/usr/bin/env python3` |
| `upstream-tests/var/` 被 gitignore | 上游 `test/.gitignore` 有 `var/*`，`var/.gitkeep` 不会进库 | ① 提交时对 `upstream-tests/var/.gitkeep` 显式 `git add -f`，保持 61/61 逐字节一致；② `build()` 里 `os.makedirs(test/var)` 兜底，避免依赖该文件 |

## 7. 已知限制

- 9 条 `ClientTest` 用例在设备上无法执行（§4.3-1）；CI worker 的 HOME 若不是
  HMDFS，这些用例可能通过，届时以 CI 日志为准。
- `DrvAdminTest` 的两条计数断言在本平台结构性失败（§4.3-2/3）。
- 依赖不可得的驱动/插件（USB、FTDI、portaudio、ALSA、systemd/udev、uinput、
  devinput）需要先发布对应依赖包才能补齐，属平台能力边界。
- `space-enc-1`/`rc6` 两条脚本在设备上有输出差异（§4.3 表），原因未进一步定位到
  单行；它们不参与 CppUnit 判定（上游不检查 `system()` 返回值）。
- CI worker 上若上游套件被本配方硬界杀掉（`rc is None`）或死于 SIGTERM（`rc == -15`）
  而没有打出汇总，本配方记 `status="aborted"`、计数全 `null` 并**不让构建失败**
  （§4.5 处置 2）：这是「如实记账」而非通过——该形态说明 worker 侧没跑到结论，判绿只能
  依据设备侧日志；其余异常退出（其它信号、126/127、`rc == 0` 却无汇总）一律硬失败。
- 上游 `test/run-tests.cpp:24` 的 `system("pkill lircd")` 与 `ClientTest` 的
  `kill(garbage_pid, SIGTERM)` 都是「按名字/按未初始化 pid」的杀进程面。前者属上游逐字
  继承、本配方不改（已在案 P3）。后者：处置 1 的 SIGTERM 忽略只消除**自指**情形
  （pid 为 0 或套件自己的 pid）；若栈残留恰好是**别的进程**的 pid（含 -1，会打到该用户
  所有可发信号进程），SIGTERM 仍会落到对方身上——`upstream-tests/` 是上游逐字副本，
  本配方刻意不改其调用点，该残余误杀面如实登记、不宣称已消除。
- `plugins/default.c` 的 devinput 面在本平台不可用（无 `/dev/input`）；§4.1-10 修的是
  「产物里有一个装好即无法加载的 `.so`」这个交付缺陷，不是让它在本平台具备功能。

## 8. 知识草稿（知识库扩展）

本 PR 随包提交 3 份知识草稿（`.kv` + `.md` 成对；`yaml.safe_load` 与
`error_signature`/`forbid_*_pattern` 的 `re.compile` 自检通过，`/tmp` 命中 0）：

| 草稿 | 主题 | 对应本文 |
|---|---|---|
| `knowledge/drafts/E4300-draft-0533.kv` | HMDFS 大小写不敏感 + 构建目录 `VERSION` 顶替 libc++ 的 C++20 `<version>` 头 | §4.1-3 |
| `knowledge/drafts/E4301-draft-5EC2.kv` | sysroot `<pthread.h>` 缺 `pthread_cancel` 声明；musl `pthread_t` 是指针 | §4.1-7/8 |
| `knowledge/drafts/E4302-draft-24AC.kv` | tarball 里发行机生成的 `lib/lirc/config.h` 在 out-of-tree 构建下压过新生成的 config.h | §4.1-4 |

**取号沿革（在线事实，非"未发生"）**：初版按最小空号取 E757/E758/E759，随后
`upstream/main` 的 `【知识库归档】20261016-03` 批次把同样三个号落给了 libdisasm 0.23
（`contents/knowledge/graph/E757.kv|E758.kv|E759.kv?ref=main` 均 200，首行 `# Software:
libdisasm 0.23`），即**最小空号在多设备/归档并发下不可靠**——本设备同期还另有
`lirc-0.10.2-a/-b/-c` 三个兄弟任务持有 E757–E759 的私有登记（`$HOME/tmp/*/.reserve-E*`）。
返修轮用 `tools/knowledge_id.py --check <ID> --fresh` 三面核查（主线基线
`upstream/main@e52fd432b`，2026-10-18）后改号为 **E4300/E4301/E4302**：当时最小空号是
E2296，而实测前沿在 12 分钟内推进 4 个号（E2299 被并发任务 lttng 占），最小空号在合并
窗口内必被占用，故按前沿 +≈2000 取号并逐个三面复核；推送前再复核一次。草稿的
`id:` / `doc_file:` / `.md` 标题 / `manifest.yaml` 的 `knowledge_ref` 已同步改名。
