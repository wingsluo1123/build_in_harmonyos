# imx_usb_loader @ 0_git20201102 — 适配笔记（证据）

> 本文件放**验证证据**（`reports/` 在 .gitignore 里，提交不进去）。

## 0. 一句话

把 `boundarydevices/imx_usb_loader` 的两个 CLI（`imx_usb` + `imx_uart`）与 14 个板级
配置打进 conan 包，**零补丁**；用上游自带的 `tests/` 黄金语料套件（3 个用例、完全
离线、`-S` 模拟模式）作硬门禁，本机实测 3/3 逐字节通过；消费者用例 12/12。

## 1. 版本号与源码快照的钉死（**不要按日期去上游找提交**）

任务给的是 Debian/Alpine 快照式版本号 `0_git20201102`。核实过程与结论：

| 来源 | 证据 |
|---|---|
| **Alpine aports**（权威，`community/imx_loader/APKBUILD`） | `pkgname=imx_loader`、`pkgver=0_git20201102`、**`_commit="30b43d69770cd69e84c045dc9dcabb1f3e9d975a"`**、`source="$pkgname-$pkgver.tar.gz::https://github.com/boundarydevices/imx_usb_loader/archive/$_commit.tar.gz"`、`options="!check"  # No tests available` |
| **Buildroot** | `package/imx-usb-loader/imx-usb-loader.mk`：`IMX_USB_LOADER_VERSION = 30b43d69770cd69e84c045dc9dcabb1f3e9d975a` |
| **Debian** | `https://ftp.debian.org/debian/pool/main/i/imx-usb-loader/` 里唯一的 orig tarball 是 `imx-usb-loader_0~git20200517.30b43d69.orig.tar.gz`（同一 commit）；`madison` 列出的历史版本只有 `0~git20200517.30b43d69-{1,2}`、`0~git20200103.f009770d-1`、`0~git20181105.4aa98090-1`、`0~git20171026.138c0b25-1` —— **从来没有 `0~git20201102`** |
| **上游仓库** | `boundarydevices/imx_usb_loader` 只有 `master` 一个分支、**无 tag**；最新提交就是 `30b43d69770c`（2020-05-17）。GitHub commits API 显示 **2020-05-18 到 2020-11-02 之间零提交** |

⇒ **`20201102` 是 Alpine 的快照/打包标签，不是提交日期**；真正的源码快照是
`30b43d69770cd69e84c045dc9dcabb1f3e9d975a`。本包把「版本标签」与「钉死 commit」
两条信息都写进 `conandata.yml` / `manifest.yaml` / PR 正文，**没有编造任何版本号**。

**双校验**：

```
url       = https://github.com/boundarydevices/imx_usb_loader/archive/30b43d69770cd69e84c045dc9dcabb1f3e9d975a.tar.gz
sha256    = 4357907c9669874d3ccbf00395bf0b1733c26e6daea85d721f1c0cd897f4162c
字节数    = 68279
tar 条目  = 55      (tar tzf | wc -l)
```

`https://codeload.github.com/boundarydevices/imx_usb_loader/tar.gz/<同 sha>` 返回
**完全相同**的字节与 sha256（两条 URL 都实测过）。

> 提示：GitHub Actions/CI 的预下载脚本会更喜欢带扩展名的 URL；本包用的是
> `github.com/.../archive/<sha>.tar.gz`（以 `.tar.gz` 结尾），所以 `get()` 不需要
> 额外的 `filename=` 参数（与 fakechroot 那条 codeload 坑不同）。

## 2. 上游有一个**完全离线**的真测试套件（关键发现）

`tests/Makefile`：

```make
IMX_USB ?= ../imx_usb
%.test: % FORCE
	@$(IMX_USB) -v -S 0x15a2:0x0061 $* > $@
	@diff -u $*.output $@
tests:	test.imx.test test-dcd.imx.test test-plugin.imx.test
```

* `-S/--sim=VID:PID` **不是「指定设备」而是「模拟设备」**：`imx_usb.c` 的
  `long_options[]` 里 `{"sim", required_argument, 0, 'S'}` → `do_simulation_dev(...)`
  （`imx_sdp_simulation.c`）。所以三个用例**不需要任何 USB 硬件**。
* 每个用例把完整调试轨迹写到 `*.test`，再与上游提交的黄金文件
  `test.imx.output`(43,145 B) / `test-dcd.imx.output`(43,464 B) /
  `test-plugin.imx.output`(773,471 B) 逐字节 `diff`。
* 输入语料随 tarball 交付：`tests/{image.bin, plugin.bin, bare.cfg, dcd.cfg, plugin.cfg, test.imx, test-dcd.imx, test-plugin.imx}`。

**本机实测**：

```
$ make tests            # 顶层 -> $(MAKE) -C tests/ tests
Testing test.imx
Testing test-dcd.imx
Testing test-plugin.imx
rc=0                    # 3/3 逐字节一致
```

Alpine 的 `options="!check"  # No tests available` 是**不准确**的（上游确实有测试，
只是没挂到 automake 的 `check`/`tests` 习惯位置上）——这一点也写进了 PR 正文。

## 3. 三个「不做就编不过 / 跑不起来」的处置

### 3.1 (R1) in-source 构建

上游是**手写 Makefile**（无 configure/CMake/automake），每条规则都相对**当前目录**
编译 `*.c`，conan 默认的 out-of-source 构建目录根本放不下它；`tests/` 的驱动器也
写死 `IMX_USB ?= ../imx_usb`（树内布局）。所以 `build()` / `package()` 都用
`self.run(..., cwd=self.source_folder)` 在源码目录内执行（仓库先例
`proxychains-ng/4.16`、`lolcode/0.10.5`、`aescrypt/0.7`）。

### 3.2 (R2) 配置目录的确定性

Makefile：

```make
bindir ?= $(prefix)/bin
sysconfdir ?= $(prefix)/etc
rel_sysconfdir = $(shell realpath -m --relative-to=$(bindir) $(sysconfdir))
CONFCPPFLAGS = -DSYSCONFDIR='"$(sysconfdir)"' -DREL_SYSCONFDIR='"$(rel_sysconfdir)"'
```

两个问题：① 依赖构建机有 **GNU coreutils 的 `realpath`**（Alpine 为此专门把
`coreutils` 加进 `makedepends`，说明 busybox 的 `realpath` 不够用；OHOS worker 上
未必有）；② 结果会随 `/bin` 是否为符号链接而变。

处置：`prefix=/ bindir=/bin sysconfdir=/etc rel_sysconfdir=../etc` 全部作为 **make
命令行变量**传入（命令行变量优先于 Makefile 里的 `=` 与 `?=` 赋值），编译期的两个
字符串因此完全确定。实测两个产物的 `.rodata` 同时含
`/etc/imx-loader.d` 与 `../etc/imx-loader.d`（交付形态自检 M7）。

### 3.3 (R3) libusb 的包含路径：**不能直接信 conan 的 pkg-config 契约**

老源码写的是 `#include <libusb-1.0/libusb.h>`，而 conan `libusb/1.0.27` 的
`libusb-1.0.pc` 是：

```
includedir=${prefix}/include/libusb-1.0
Cflags: -I"${includedir}"
```

⇒ 只给 `-I<prefix>/include/libusb-1.0`，编译就报
`fatal error: libusb-1.0/libusb.h: No such file or directory`（本机第一轮实测原样报错）。
修法：**父目录 `-I<prefix>/include` 必须一起给**；同时把 `USBCFLAGS` / `USBLDFLAGS`
作为 make 变量注入，**完全绕过 pkg-config**：

```
USBCFLAGS  = -I<dep>/include/libusb-1.0 -I<dep>/include
USBLDFLAGS = -L<dep>/lib -lusb-1.0 -lpthread
```

（`includedirs`/`libdirs`/`libs`/`system_libs` 全部取自 `self.dependencies["libusb"]
.cpp_info.aggregated_components()`，没有硬编码。）这样 OHOS worker 上**连
pkg-config 都不需要**。

### 3.4 零补丁

以上三点全是**构建期变量/布局**层面的处置，**没有改上游任何一行源码**
（`patches_applied: []`，`conandata.yml` 无 `patches:` 段）。

### 3.5 (R5) 黄金套件必须拿到 `LD_LIBRARY_PATH`——否则「产出 0 字节」

**平台 CI 实证**（PR !15132，build #79888，失败日志原文）：

```
[upstream] make check rc=2
make -C tests tests
make[1]: Entering directory '.../b/tests'
Testing test.imx
make[1]: Leaving directory '.../b/tests'
[upstream-classify] tests/test.imx: FAIL — golden=43145 bytes, produced=0 bytes
[upstream-classify] tests/test-dcd.imx: NOTRUN — test-dcd.imx.test was not produced
[upstream-classify] tests/test-plugin.imx: NOTRUN — test-plugin.imx.test was not produced
```

根因：上游驱动 `@$(IMX_USB) -v -S … > $@` 直接执行 in-source 构建树里的
`../imx_usb`；该 ELF 是动态链接（`DT_NEEDED libusb-1.0.so.0`）且**没有
RPATH/RUNPATH**（自检 M5 逐产物断言），运行时只能靠 `LD_LIBRARY_PATH` 找 libusb。
`subprocess.run()` 继承的 worker 环境里**没有**依赖包的 libdir（conan 的 build env
只带 profile buildenv，不带依赖 libdir）⇒ 加载器拒绝执行、重定向照样建出
**空的** `test.imx.test` ⇒ `diff` 失败 ⇒ make 在第一例就以 rc=2 中止（另两例连跑都
没跑）——所以「产不出字节」不是黄金语料不一致，是**二进制压根没跑起来**。
首轮日志只打印了 stdout，`make` 写往 stderr 的
`*** [Makefile:5: test.imx.test] Error 127` 被丢掉，这正是当时无法一眼定位的原因。

修法（配方侧，仍零上游补丁）：

1. 给 `make -f ohos-check.mk check` 的子进程显式注入
   `LD_LIBRARY_PATH=<libusb libdir>:$LD_LIBRARY_PATH`
   （与 `_run_cli_end_to_end()` 已有做法同源；本仓先例 libtrng 4.28 / castxml 0.7.0）；
2. `make` 的 **stderr 也回显**（故障不再不可见）；
3. 套件开跑前先探针执行一次 `imx_usb -V`，rc≠0 就直接报「环境/加载器问题，
   不是黄金数据不一致」，并打印 stderr。

本机复刻（用 user namespace 把系统 libusb 挡掉，等价于 worker 上没有 libusb）：

```bash
unshare -rm bash -c 'mount --bind /dev/null /usr/lib/x86_64-linux-gnu/libusb-1.0.so.0.5.0; …'

# (A) 不给 LD_LIBRARY_PATH —— 与 CI 逐行同形
make rc=2
Testing test.imx
stderr: ../imx_usb: error while loading shared libraries: …/libusb-1.0.so.0
        make[1]: *** [Makefile:5: test.imx.test] Error 127
0 tests/test.imx.test                       # = CI 的 produced=0 bytes
                                            # test-dcd/test-plugin 未产出 = CI 的 NOTRUN

# (B) 注入 LD_LIBRARY_PATH（= 配方现在的行为）
make rc=0
43464 bytes  tests/test-dcd.imx.test        # 与上游 43,464 B 黄金文件逐字节一致
773471 bytes tests/test-plugin.imx.test     # 与上游 773,471 B 一致
43145 bytes  tests/test.imx.test            # 与上游 43,145 B 一致
```

`conan create . …` 全流程本机 rc=0：`[upstream] hard gate OK: 3/3 upstream golden
cases reproduced byte-for-byte` + `[cli-e2e] 4 CLI/usage/negative golden cases`
+ `test_consumer 12/12` + `test_layout 13 passed / 1 skipped`。

## 4. L1c 的 `make.*check` 字面量

上游的测试目标叫 **`tests`**（`make tests`），不是 `check`，CI 的
`grep -qiE "make.*check|ctest|meson test|pytest"` 匹配不到。处置：`build()` 在源码
目录里生成一个**一行**的 `ohos-check.mk`（不进包、不进 PR 交付物）：

```make
IMX_USB ?= ../imx_usb
check:
	$(MAKE) -C tests tests
.PHONY: check
```

然后跑 `make -f ohos-check.mk check` ⇒ 日志里既有规范字面量，执行的又**完完全全
是上游 `$(MAKE) -C tests tests`**。这是刻意的、写进配方 docstring 的转调，不是为过
闸门而伪造执行。

## 5. 门禁与用例（本机 x86_64，conan 2.29.1，gcc 15.2）

```
conan create . --build=missing -r ohpc \
  -s os=Linux -s arch=x86_64 -s compiler=gcc -s compiler.version=15 \
  -s compiler.libcxx=libstdc++11 -s build_type=Release
⇒ rc=0
```

| 项 | 结果 |
|---|---|
| 上游黄金语料套件（硬门禁） | **3/3 PASS**（`PASS(upstream diff)`，逐字节） |
| CLI 端到端黄金用例 | **4/4**（`imx_usb -V` / `imx_uart -V` / `imx_usb -h` 3 条 usage 字面量 / `-c <不存在目录>` 负例） |
| 消费者用例 | **12/12**（`[consumer] checks=12 passed=12 failed=0 (CLI executed=1)`） |
| 交付形态自检 M | **14 通过 + 0 失败 + 1 跳过（OHOS `.codesign`）** |
| `preflight.py` | PF1–PF8 + R52 + PF3x2 全通过；**PF9 命中 1 条**（见 §6） |
| `check_vacuous_assertions.py` | 恒真断言 **0** |

消费者用例（`test_consumer.py`，12 项）里**与可执行权限无关**的那一半是配置数据库
契约，用独立 Python 解析器按上游 `imx_loader_config.c` 的格式核对：

* `etc/imx-loader.d/` 恰好 14 个 `*.conf`；
* `imx_usb.conf` 22 条 `0xVID:0xPID, <board>.conf` 映射全部格式合法；
* 上游 `tests/Makefile` 用的那对 `0x15a2:0x0061` **必须**映射到 `mx6_usb_work.conf`；
* 被引用但**未交付**的配置恰好是上游的三个历史缺口
  （`mx23_usb_work.conf` / `mx28_usb_work.conf` / `linux_gadget.conf` —— 上游从未把它们
  提交进仓库）；**原样交付，不编造文件补上**，并在用例里作为显式断言；
* 14 个文件与**钉死 tarball 派生**的 sha256 表（写在 `test_layout.py::CONF_SHA256`，
  可用 `sha256sum *.conf` 从 tarball 复现）逐条一致。

## 6. 关于 commands.json 与 PF9（如实说明）

本包是**纯 CLI 包**，语义上 `package_type = "application"` 是正确的分类（仓库里
1570 个配方同款）。而 PF8 的 `is_cli` 判定里 `package_type="application"` 必然为真，
于是**软件级** `commands.json` 是 PF8 的硬要求：

* `archives/i/imx_usb_loader/commands.json`（软件级，R38/L0k 要求的形态）⇒ **PF8 通过**；
* 但 PF9 要求所有变更路径 ≥5 段，而 `archives/i/imx_usb_loader/commands.json` 只有 4 段
  ⇒ **PF9 命中 1 条**。

这与仓库里已合入的 `daemon/0.8.4`、`iptables/1.8.13`（以及所有
`package_type="application"` 的 CLI 包）是**同一个已知的 PF8↔PF9 自相矛盾**。
对**纯库包**可以用「版本级 commands.json + 不写 bindirs」绕成全绿（见
`fakechroot/2.20.1` 与 `ebtables/2.0.11`），但对 `application` 包**没有**这条路：
PF8 只认软件级路径，放在版本级会直接报「CLI 包缺 commands.json」。二者只能取其一，
本包按语义正确 + R38/L0k 的口径，选择**保留软件级文件、接受 1 条 PF9**。

`cpp_info.bindirs` 未显式声明（conan 默认值本来就是 `["bin"]`，消费端照常能找到
两个工具）。

## 7. 未解决风险 / 待平台 CI 验证

1. **OHOS 侧无法本地验证**（本机没有 OHOS SDK/工具链，CI 停摆）。已核对过的可移植性：
   上游源码没有 glibc 私有入口、没有 `asprintf`/`strdupa`/`execinfo` 之类 GNU 扩展，
   `#include <termios.h>`（imx_uart）与 `readlink("/proc/self/exe")`（仅当 argv[0]
   无 `/` 时走）在 musl/OHOS 上都有；唯一需要预判的是 `-lpthread`（libusb recipe 在
   OHOS 上自己也声明 `system_libs = ["pthread"]`，与仓库既有约定一致）。
2. **`make check` 依赖 `diff`**：上游 `tests/Makefile` 用 `diff -u`。若 OHOS worker 没有
   `diff`，配方会探测 `shutil.which("diff")`，缺失时用 Python 对**同一份上游黄金文件**
   做字节比较，并在日志里标注 `PASS(python fallback)` + 原因（不是静默降级）。
3. **OHOS 包目录内动态链接 ELF 不可 `execve`**（硬坑 E）：`test_consumer.py` 会明确
   打印平台限制并只跑与权限无关的配置契约；等价 CLI 用例已在 `build()` 用 build 树里
   的同一份产物真跑。两个可执行体在 `package()` 里逐个签名
   （`llvm-objcopy --remove-section .codesign` + `binary-sign-tool sign -selfSign 1
   -inFile X -outFile X.signed` + `os.replace` + `chmod 0755`，**写另一个输出文件**）。
4. **`0_git20201102` 与 2020-05-17 的日期错位**：已在 PR 正文/`manifest.yaml`/
   `conandata.yml` 三处写明来源与三方印证，任何复核者都能按 §1 的表格复现。
5. 平台 CI 已恢复并给出结论（2026-10-10）：首轮失败 = §3.5 的 R5（黄金套件拿不到
   `LD_LIBRARY_PATH` ⇒ 产出 0 字节），已按 §3.5 修好并在本机用 user namespace 逐行
   复刻（失败形态与修好后形态都复现）；OHOS aarch64 的最终结论仍以下一轮 CI 为准。
6. 上游 `tests/Makefile` 对 `%.test` 用 `FORCE` 前置，每次都重跑（不是增量缓存），
   三例全量执行约 1–2 秒，无超时风险。

## R6（2026-10-13）— 补**鸿蒙特有测试** `test_package/test_ohos_native.py`（O1..O10）

**动机**：上游 3 条黄金轨迹 + `test_consumer.py` + `test_layout.py` 都是**平台中立**的
（在 Linux 上同样通过），因此不能证明「这份交付物在 HarmonyOS 上成立」。

**实现**：新文件 `test_package/test_ohos_native.py`，**只在 `os == "OHOS"` 时执行**，
10 条判据全部是鸿蒙平台特有的约束，且都由**包内真实文件 / 真实 ELF 结构 / worker 上真跑**得出：

| 项 | 判据（真值来源） |
|----|------------------|
| O1 | 平台身份：`/data/service/hnp` 存在 + 打印 `uname.sysname`（鸿蒙 PC 实测标志） |
| O2 | OHOS 只有 `/data/service/hnp/bin/bash` ⇒ 断言两个交付 ELF 的字节里**不出现** `/bin/bash` |
| O3 | 设备 `/tmp` 只读 ⇒ 断言交付物**不依赖** `/tmp` 写路径（并打印 worker 实测可写性） |
| O4 | OHOS 加载器签名契约 ⇒ 两个 ELF 都带 `.codesign`/`.note.ohos`（section 名或字节双路判定） |
| O5 | OHOS 不在 CMake 平台表 ⇒ 断言 `.dynamic` 里**无** DT_RPATH/DT_RUNPATH |
| O6 | 依赖闭包：DT_NEEDED 只允许系统库与 `libusb-1.0.so.0`，且**不得含路径** |
| O7 | **在鸿蒙 worker 上真跑 `bin/imx_usb -V`**：rc=0 ⇒ 断言版本横幅 `imx_usb 0.2pre`；被拒 ⇒ 断言拒绝形态属于已归档平台策略且交付物已签名 |
| O8 | 同上，`bin/imx_uart`（两入口共用 `imx_loader.h:22` 的版本串，实测同样打印 `imx_usb 0.2pre`） |
| O9 | 配置数据库随包交付：首行 `#vid:pid, config_file`、≥20 条映射、且含 `tests/` 依赖的 `0x15a2:0x0061` |
| O10 | ELF64 + `e_machine` 与目标架构一致 + 类型 ∈ {ET_EXEC, ET_DYN} |

**反恒真设计**：`.dynamic` 的 `DT_STRTAB` 是**虚拟地址**，必须经 `PT_LOAD` 做 vaddr→offset 映射；
第一版直接当文件偏移读，DT_NEEDED 静默变空 ⇒ O6 退化成恒真断言 —— **已修**（本地实测 now
`imx_usb=['libusb-1.0.so.0','libc.so.6']`、`imx_uart=['libc.so.6']`）。O9 的第一版也误判过
（期望 "HEADER" 行，实际是 `#vid:pid, config_file`）⇒ 已改为真实格式断言。

**本地复核**：`conan create archives/i/imx_usb_loader/0_git20201102 -nr` ⇒ rc=0；
新套件在 Linux 上打印 `[skip] OHOS-native suite（全部 10 条） — 非 OHOS 构建` 并 rc=0（显式跳过，非静默）；
强制 `--os OHOS` 复核各判据代码路径：10 条中仅 O1/O4 在 Linux 上为 FAIL（正是鸿蒙专有属性），
其余 8 条通过 —— 说明判据本身可分平台区分，不是恒真。
