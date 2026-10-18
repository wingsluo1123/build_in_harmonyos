# lttng-ust 2.12.10 适配笔记（HarmonyOS PC / aarch64）

> 任务：ohpcd rawId 15599（开源鸿蒙PC专项积分赛-依赖）· 分支 `feat/lttng-ust-2.12.10`
> 包目录：`archives/l/lttng-ust/2.12.10/` · 执行日期：2026-10-18

## 1. 软件与源码

| 项 | 值 |
|---|---|
| 上游项目 | lttng-ust（LTTng userspace tracing library），<https://lttng.org/> |
| 版本 | 2.12.10（stable-2.12 分支） |
| 上游 tag | `v2.12.10` = `6de183f5ea81ed551546ee955a86caf7e966e400` |
| 官方 tarball | `https://lttng.org/files/lttng-ust/lttng-ust-2.12.10.tar.bz2` |
| sha256 | `aa802851c6d08c653ac1dd7da8f552baaa5d87e9b03c2d6a8b7a04322e53dc47` |
| 字节数 | 801458 |
| 构建系统 | autotools（`configure` + `make`，tarball 自带预生成 configure/man 页） |
| 产物 | `liblttng-ust.so`、`liblttng-ust-tracepoint.so`、`liblttng-ust-ctl.so`、`liblttng-ust-{fd,fork,dl,libc-wrapper,cyg-profile,cyg-profile-fast}.so`、`include/lttng/*.h`、`bin/lttng-gen-tp` |

取数命令（本地复算，与任务卡给的读数逐字一致）：

```sh
cd "$HOME/tmp/kbscan/lttng-ust"
stat -c '%s' lttng-ust-2.12.10.tar.bz2          # 801458
sha256sum lttng-ust-2.12.10.tar.bz2             # aa802851c6d0…e53dc47
```

## 2. W0 生死关结论（三条，全过）

| 判据 | 结果 | 证据 |
|---|---|---|
| W0-1 版本可得性 | ✅ | 上游 tag 实核存在 + 官方 tarball 可下载，size/sha256 双读数一致（见 §1） |
| W0-2 硬依赖 | ✅ | 唯一硬依赖 `liburcu`（ohpcd 已发布 `liburcu/0.15.6`、`0.15.7`）。**本包不需要 popt**：全树 `grep -rn popt` 0 命中，`configure.ac` 0 处 `PKG_CHECK_MODULES`（popt 是 lttng-tools 的依赖，不是 lttng-ust 的） |
| W0-3 平台不可移植判据 | ✅ | ISA 专属头（`altivec.h`/`mmx.h`/`xmmintrin.h`/`immintrin.h`/`ppc_asm.h`…）0 命中；glibc printf 钩子（`register_printf_*`/`<printf.h>`）0 命中 |

**硬依赖实查**（R35：不用 `conan list` 判可得性）：

```sh
conan download "liburcu/0.15.6" -r=ohpcd --only-recipe     # rc=0
```

`configure.ac` 的依赖探测面（无 pkg-config）：

```
AC_CHECK_HEADERS([urcu-bp.h])                       # 头
AC_CHECK_LIB([urcu-cds], [_cds_lfht_new])           # 库
AC_CHECK_LIB([urcu-bp],  [urcu_bp_synchronize_rcu])
AC_CHECK_LIB([urcu-bp],  [urcu_bp_call_rcu])        # >= 0.11
AC_CHECK_LIB([numa],     [numa_available])          # 默认 enable ⇒ 必须 --disable-numa
```

## 3. 家族配方陷阱：逐条复核结果

派发卡列出上一轮 lttng-tools 2.12.10 已踩出的 4 条陷阱，本包逐条复核：

| # | 陷阱 | 本包是否命中 | 处置 |
|---|---|---|---|
| ① | `AutotoolsDeps` 注入包内不存在的库名 → `C compiler cannot create executables` | ⚠️ 规避（未命中） | 本包**不使用** `AutotoolsDeps`：`liburcu/0.15.6` 的 `cpp_info.libs` 列了全部 7 种 flavor（urcu/urcu-bp/urcu-cds/urcu-common/urcu-mb/urcu-memb/urcu-qsbr），全量塞进 `LIBS` 会把用不到的目标码拉进来；只注入 `-I/-L`，让 configure 的 `AC_CHECK_LIB` 决定真正需要的 `-lurcu-*`。**同时**修正了本包 `package_info()`：只列包内真实存在的 `lttng-ust` / `lttng-ust-tracepoint`（上游 2.15.1 配方列的 `lttng-ust-provider` 在已发布包里并不存在——这正是 lttng-tools 那轮 configure 崩的根因，本包不再复现该缺陷） |
| ② | `PkgConfigDeps` 只生成按包名一份 `.pc`，家族多个 `.pc` 缺失 | ❌ 未命中（结构性不适用） | 2.12.10 全树 **0 处** `PKG_CHECK_MODULES`（实测 `grep -rn PKG_CHECK configure.ac m4/` 空），根本不读 `.pc`，故不引入 `PkgConfigDeps` |
| ③ | 配方 `buildenv_info` 不进本包构建环境 ⇒ `PKG_CONFIG_PATH` 静默失效 | ✅ 命中（同类） | `TMPDIR` 必须走 `Environment().save_script("conantmpdir")` 才生效（`buildenv_info` 只传给消费者）。本包不设 `PKG_CONFIG_PATH`（无 pkg-config 使用面） |
| ④ | `configure` 的 `$ac_tmp` 用 `umask 077` 在 HMDFS 落 0700 目录不可写 → `config.status: could not setup config files machinery` | ✅ **命中并复现** | `patches/0003-configure.patch` 把两处 `umask 077` 改 `022`。**实测关键事实：toybox `mktemp -d` 遵循 umask**（`(umask 077 && mktemp -d)` → `drwx--S--- 2700`，`touch` 直接 Permission denied；`umask 022` → 可写）——这与 GNU coreutils 的 `mktemp -d` 硬编码 0700 不同，是本平台专属形态 |
| ⑤ | `liburcu/0.15.6` 包内 `.la` 的 `libdir=/` → `libtool: error: '…' is not a valid libtool archive` | ✅ **命中并复现** | 见 §4.2。配方侧 `_relocate_dep_libtool_archives()` 拷贝 + 重写，依赖包本体不动 |

**engine 命中情况**：上述 4 条（config.guess / config.status-umask / libtool-.la / dlclose）
在知识库中均有既有条目（`DRAFT-E678`/`E737`/`E715`/`DRAFT-libfreefare-0.4.0`/`E013` 等），
故**不新建**这些草稿。本次新建两份草稿，均为 engine 未命中且与既有条目的建议**相反或缺失**：
① `E4310-draft-8CAA`（平台 POSIX shm 映射首次访问即 SIGSEGV，直接否证
`E1940`/`E2070` 的「改用 POSIX `shm_open`+`mmap`」建议）；
② `E4311-draft-4DB5`（conan Release 的 `-DNDEBUG` 打断 `<assert.h>` 传递链 ⇒
共享库 `UND assert` ⇒ OHOS 加载期 relocation 失败；既有 NDEBUG 条目
（`DRAFT-cpp-member-accessor` / `DRAFT-libnih`）讲的是「断言恒真空壳」与
「assert 副作用被吞」，与本坑不同）。

## 4. 配方要点与实测

### 4.1 portability 补丁（0001–0003）

```sh
# 0001 config/config.guess：uname -s = HarmonyOS ⇒ 未打补丁时落到编译探针分支，
#      在 HMDFS 上 dummy.c 不可写而以 rc=1 "unable to guess system type" 退出
$ sh config/config.guess                      # 补丁前 rc=1；补丁后 aarch64-unknown-linux-ohos
# 0002 config/config.sub：OS 合法性表补 ohos*、kernel-os 组合表补 linux-ohos*
$ sh config/config.sub aarch64-unknown-linux-ohos    # 补丁前：OS `ohos' not recognized
$ sh config/config.sub aarch64-linux-ohos            # 三元组形态同样接受（conan 自动 --host 用这个）
# 0003 configure：两处 (umask 077 && mktemp -d/mkdir) → umask 022
```

回归核对（补丁不误伤其他目标）：
`x86_64-pc-linux-gnu → x86_64-pc-linux-gnu`、`aarch64-unknown-linux-gnu → aarch64-unknown-linux-gnu`、
`arm-linux-androideabi → arm-unknown-linux-androideabi`（均与未打补丁时同形）。

### 4.2 依赖包 `.la` 缺陷（实测命中，配方侧重定位）

liburcu/0.15.6 包内 **7 个 `.la` 全部**带 `libdir='//lib'`，且 `dependency_libs`
里既有构建机私有前缀又有不存在的路径：

```
$ grep -H '^libdir' $URCU/lib/*.la
liburcu-bp.la:libdir='//lib'          （7/7 同）
$ grep '^dependency_libs' $URCU/lib/liburcu-bp.la
dependency_libs=' -L/storage/Users/currentUser/usr/local/lib //lib/liburcu-common.la'
```

未处置时 `make` 直接失败（本机实测逐字）：

```
libtool: warning: library '…/liburcu-bp.la' was moved.
libtool:   error: '//lib/liburcu-common.la' is not a valid libtool archive
make[2]: *** [Makefile:668: liblttng-ust-tracepoint.la] Error 1
```

处置（同 libmongo-client `_relocate_pkgconfig()` 先例，**只改配方侧副本**）：
`_relocate_dep_libtool_archives()` 把依赖的 `.la` 拷到 `$GENERATORS/dep-libtool-archives/`，
重写 `libdir=` 为真实 libdir、把 `dependency_libs` 里的 `-L` 只保留指向真实依赖
libdir 的项、把 `.la` 引用改指副本，并把这个目录放在 `-L` **首位**。
落盘自检（须按"已知 .la 名单"判断，不能按"副本是否已存在"——首版实现按后者
判断，早处理的 `.la` 看不到晚处理的副本，导致 `dependency_libs` 漏改）：

```
$ grep -E '^(libdir|dependency_libs)' $RELOC/liburcu-bp.la
dependency_libs='…/dep-libtool-archives/liburcu-common.la'
libdir='…/liburcu/0.15.6/…/p/lib'
```

处置后 `make` rc=0。**这是依赖制品质量问题**（`libdir='//lib'` + 构建机私有
前缀），建议制品侧修复；配方侧定位已在 PR 正文「已知限制」点名。

### 4.3 第四条补丁：`include/lttng/tracepoint.h` 的 `dlclose()` abort

未处置时**任何**使用 `tracepoint.h` 的消费者程序（含只用 `tracef()`）在退出时被打死：

```
$ ./tests/ctf-types/ctf-types
Hello, World!
Tracing...  done.
Error (-1) in dlclose
Segmentation fault (core dumped)      # rc=139
```

`dlclose()` 对本库自己 `dlopen` 的 handle 返回 -1，上游代码
`if (ret) { fprintf(stderr, "Error (%d) in dlclose\n", ret); abort(); }`（两处：
`tracepoint.h:399-404` 与 `:541-546`）随后 abort。补丁把 abort 降级为警告并继续
清空缓存句柄（与**已发布**的 lttng-ust/2.15.1 配方同款处置，该版本是 inline
`_patch_tracepoint_dlclose()`；本包作为 patch 文件更可复核）。补丁后
`tests/hello` / `tests/ctf-types` / 消费者探针均 rc=0（见 §5 除外项）。

### 4.4 其他配方要点

| 要点 | 原因 |
|---|---|
| `--build/--host=aarch64-unknown-linux-ohos`（同值 ⇒ cross_compiling=no） | 让 configure 能真跑探测程序（本机构建） |
| `--disable-numa` | configure 默认 `--enable-numa`，numa 探测失败即 `AC_MSG_ERROR` |
| `--disable-man-pages` | tarball 已带预生成 man 页，平台无 asciidoc/xmlto |
| `--enable-shared --disable-static` | configure 硬性要求共享库（`configure.ac:104-109`：`LTTng-UST requires shared libraries to be enabled`），故 `default_options = {"shared": True}` |
| `-Wl,--allow-shlib-undefined` | OHOS/musl 把 libpthread 合并进 libc；lld 的 `--no-allow-shlib-undefined` 会对 `pthread_*` 误报未定义 |
| `env.define("TMPDIR", build_folder)` + `save_script` | autoconf `$ac_tmp` 与 config.guess 探针默认落 `/tmp`（本设备只读）；`buildenv_info` 不进本包构建环境 |
| 无 `AutotoolsDeps` / 无 `PkgConfigDeps` | 见 §3 ①② |

### 4.5 conan Release 的 `-DNDEBUG` 会打断 `<assert.h>` 传递链（自研坑，实测两轮才定位）

**现象**：`conan create` 构建成功、`package()` 成功，进入 `test_package` **执行**阶段立刻失败：

```
Error relocating /…/p/lib/liblttng-ust.so.0: assert: symbol not found
ConanException: Error 127 while executing
```

构建日志里**只有警告、没有错误**（grep 可得 6 处）：

```
liblttng-ust/lttng-events.c:188:2: warning: call to undeclared function 'assert';
liblttng-ust/lttng-events.c:204 / :624 / :647（同）
liblttng-ust/lttng-ust-statedump.c:389:4: warning: …
liblttng-ust/ust-core.c:78:3: warning: …
```

**根因**：liburcu 的 `include/urcu/assert.h` 是**条件包含**——

```c
#ifdef NDEBUG
# define urcu_posix_assert(_cond) _urcu_use_expression(_cond)
#else
# include <assert.h>
# define urcu_posix_assert(_cond) assert(_cond)
#endif
```

而 lttng-ust 的 3 个 TU（`liblttng-ust/lttng-events.c`、
`liblttng-ust/lttng-ust-statedump.c`、`liblttng-ust/ust-core.c`）**自己没写
`#include <assert.h>`**，只靠 `<urcu/uatomic.h>` → `urcu/uatomic/uassert.h` →
`urcu/assert.h` 这条链把它带进来。conan 的 `AutotoolsToolchain` 在
`build_type ∈ {Release, RelWithDebInfo, MinSizeRel}` 时把 `self.ndebug = "NDEBUG"`
注入 `CPPFLAGS` ⇒ 链断 ⇒ 这些 TU 把 `assert()` 当**未声明函数**调用 ⇒
`liblttng-ust.so` 留下 `UND assert`。

链路在链接期完全静默（libtool 默认不加 `--no-undefined`，配方又加了
`-Wl,--allow-shlib-undefined`），而 glibc 恰好导出兼容符号 `assert` ⇒ 只有在
**换 libc**（glibc→musl/OHOS）时才暴露，且因为是**加载期**失败，消费者 `main()`
里的日志一行都打不出来。

**处置**：配方 `generate()` 里 `tc.ndebug = None`（清掉 conan 注入的 NDEBUG）。
上游 autotools 的默认 CFLAGS 是 `-g -O2`、**不定义 NDEBUG**，所以这等于回到上游
构建语义。

判据（可复算）：

```sh
# 产物侧：正常只应见 UND __assert_fail；出现 UND assert 即命中
readelf --dyn-syms <pkg>/lib/liblttng-ust.so.0.0.0 | grep -w assert    # 现在输出为空
grep -c "undeclared function 'assert'" <build-log>                     # 现在为 0
```

对照实验：同一份源码手工构建（`CFLAGS=-g -O2`，无 `-DNDEBUG`）→ `UND __assert_fail`、
运行 rc=0；conan Release（带 `-DNDEBUG`）→ `UND assert`、运行 rc=127。已沉淀为
`knowledge/drafts/E4311-draft-4DB5.kv/.md`。

### 4.6 `tools/lttng-gen-tp` 的 shebang 需要 python3（conan-verify 的 L2 门禁）

`make install` 会把 `tools/lttng-gen-tp` 装到 `bin/`，而它是
`#!/usr/bin/env python` 的 Python 脚本；平台**只有 `python3`、没有 `python`**，
于是 conan-verify 的 **L2「平台功能矩阵」恒 FAIL**：

```
## L2: ❌ FAIL
  ⚠️ lttng-gen-tp: --version/--help/-V/-h 均未返回 0
  ❌ 所有二进制文件均无法运行
```

脚本本身是 py2/py3 兼容写法（`from __future__ import print_function`，
`python3 -m py_compile` 通过），实测 `python3 lttng-gen-tp --help` **rc=0**。
故 `patches/0005-tools-lttng-gen-tp-python3.patch` 只改 shebang 为
`#!/usr/bin/env python3`（同族先例：`archives/c/cloud-utils*/patches` 的
python3 shebang 补丁）。修复后 L2 转 PASS。

**附带限制（不影响 L2）**：`lttng-gen-tp <file>.tp` 的默认模式还会顺手生成
`.o`，其 `ObjFile.write()` 在找不到 C 编译器时抛 `RuntimeError: No C Compiler
detected`（它自己探测 `cc`/`gcc`，不认 `clang`）。实测 `.h` / `.c` 两个产物已正确
生成（`doc/examples/gen-tp/sample_tracepoint.tp` → 593B `.h` + 146B `.c`），
只是最后 `.o` 一步报错。不改上游：这是工具的可选加速步骤，用
`--help` 之外的模式时可按需传 `--no-object`（若该版本支持）或忽略最后一步。

## 5. 上游测试与 N 清点

### 5.1 N 的候选数法（四种口径，取最大值）

| 口径 | 读数 | 逐字取数命令（均在本包源码树内执行、已实跑） |
|---|---|---|
| ① automake `TESTS` 注册数 | **4** | `grep -n -A3 '^TESTS' tests/Makefile.am` |
| ② `tests/` 下 `noinst_PROGRAMS` 程序数 | **12** | `grep -rhE '^noinst_PROGRAMS' tests/*/Makefile.am \| sed 's/^noinst_PROGRAMS *= *//' \| tr ' ' '\n' \| grep -vE '^$\|\\' \| wc -l` |
| ③ 源码静态 `ok(` 调用点 | **20** | `grep -rcE '\bok[[:space:]]*\(' tests/*/*.c tests/*/*.cpp \| awk -F: '{s+=$2} END{print s}'` |
| ④ 各用例 `plan_tests()` 声明数之和 | **88** | `grep -rn 'plan_tests(' tests/ --include='*.c' --include='*.h'` → `1`（snprintf）`+ NUM_TESTS(2)`（gcc-weak-hidden）`+ parse_test_data_len+1 = 36+1 = 37`（test_smp）`+ NUM_ARCH(4)×NUM_TESTS_PER_ARCH(11)+NUM_TESTS_PIC(3)+1 = 48`（ust-elf） |

②的逐字输出（12 行，含 `hello`×3 属不同目录的同名程序）：

```
noinst_PROGRAMS = bench1 bench2        noinst_PROGRAMS = test_smp
noinst_PROGRAMS = ctf-types            noinst_PROGRAMS = same_line_tracepoint
noinst_PROGRAMS = test_gcc_weak_hidden noinst_PROGRAMS = test_snprintf
noinst_PROGRAMS = hello-many           noinst_PROGRAMS = hello      (tests/test-app-ctx)
noinst_PROGRAMS = hello  (tests/hello) noinst_PROGRAMS = ust-elf
noinst_PROGRAMS = hello  (tests/hello.cxx, 条件 CXX_WORKS)
```

**N = 88（取最大值，口径 ④）**。差额归因（88 − 4 = 84、88 − 12 = 76、88 − 20 = 68）：
`TESTS` 注册的是**测试程序**（4 个），而 TAP 的计数单位是**测试点**——`plan_tests(N)`
声明的是本次运行会输出多少条 TAP 结果，框架据此判定 `too few tests run`。其中
`ust-elf/test_ust_elf` 的 48 = `NUM_ARCH(4)×NUM_TESTS_PER_ARCH(11) + NUM_TESTS_PIC(3) + 1`；
`libringbuffer/test_smp` 的 37 = 36 条表驱动用例 + 1；静态 `ok(` 只有 20 处是因为
两个用例把断言写在**循环/子函数**里（`test_smp` 的 36 条来自 `parse_test_data[]`，
`ust-elf` 的 44 条来自 `test_elf()`×4 架构 + `test_pic()`）。
`doc/examples/` 下的样例是 `make` 期的**编译面**、不注册为 `TESTS`，不计入 N。

### 5.2 实测（分组跑，LOG_COMPILER 只对脚本型用例成立）

```sh
# A 组：不加载 liblttng-ust 的 3 个二进制用例（硬门禁）
make -C tests check TESTS="snprintf/test_snprintf gcc-weak-hidden/test_gcc_weak_hidden libringbuffer/test_smp"
#   → rc=0  TOTAL 40 / PASS 40 / FAIL 0 / SKIP 0 / ERROR 0

# B 组：唯一链接 liblttng-ust 的脚本用例（shebang 是 #!/bin/bash，平台无 /bin/bash
#      ⇒ 按 notes/device-facts.md §一.16 用 LOG_COMPILER 传绝对路径 bash，不改上游脚本）
make -C tests check TESTS="ust-elf/test_ust_elf" LOG_COMPILER=/data/service/hnp/bin/bash
#   → rc=2  TOTAL 9 / PASS 7 / FAIL 0 / ERROR 2（too few tests run / status 139）
```

必须分组的原因：`LOG_COMPILER` 是**全局**变量，混跑时 A 组的 ELF 二进制会被
`bash` 当脚本执行 → `missing test plan` + `exited with status 126`（实测首轮
`TOTAL 20 / PASS 12 / ERROR 8` 就是这么来的）。

### 5.3 计数结论（TOTAL = PASS + FAIL + SKIP + NOT_RUN）

| 项 | 值 |
|---|---|
| TOTAL（N） | **88** |
| PASS | **40** |
| FAIL | 0 |
| SKIP | 0 |
| NOT_RUN | **48** |

- PASS 40 = `test_snprintf` 1 + `test_gcc_weak_hidden` 2 + `test_smp` 37。
- NOT_RUN 48 = `ust-elf/test_ust_elf` 的 48 个测试点**无法跑完**。原因是**环境**：
  本机 `/dev/shm` 被写满（Avail=0），liblttng-ust 的 `ust_listener` 线程在
  `wait_for_sessiond()` 里读 shm 映射时被 SIGSEGV 终止（机制与逐字读数见 §6）。
  **不是包缺陷、也不是配方失败**——`/dev/shm` 恢复空间后同一份提交应能取得该用例的
  干净读数（本会话内无法清理该共享 tmpfs）。
  该用例每次运行会先跑完 7–12 条断言（均 PASS）再被平台 SIGSEGV 打断，条数每次
  不同（12 / 7 两次实测），故按最保守口径**整体计入 NOT_RUN**，不把那 7–12 条
  并进 PASS（避免与"跑完"混淆、也避免与 PASS 40 重复计数）。
- 该用例不是断言失败：`FAIL 0`，报的是 `too few tests run` + `status 139`。

**鸿蒙侧消费者用例（分栏，不并入上游分母）**：

| 项 | 值 | 说明 |
|---|---|---|
| test_package 断言 | **5 / 5 PASS** | 版本宏 ×2 + `tracef()`/`tracelog()` 可链接可调用 ×2 + 真实 `TRACEPOINT_EVENT` 注册与触发 ×1 |
| 稳定性 | 60/60 | 同一探针连跑 60 次全 rc=0（另 60 次 `tracef` 单点探针亦 60/60） |

### 5.4 未运行的用例（NOT_RUN 明细）

| 用例 | 未运行原因 | 影响范围 |
|---|---|---|
| `ust-elf/test_ust_elf`（48 个测试点） | **环境**：本机 `/dev/shm` Avail=0（§6）。链接 liblttng-ust 即加载其构造函数，`ust_listener` 线程在 `wait_for_sessiond()` 读 shm 映射时被 SIGSEGV 终止（空间耗尽被呈现为不可捕获的 SIGSEGV） | ELF 解析 API（`lttng_ust_elf_*`）的完整 4 架构 + PIC 覆盖在本轮未取得通过读数；前 7–12 条（x86 架构的 memsz/build-id/debuglink）实测 PASS，可作部分覆盖证据。空间恢复后应重跑该用例 |

## 6. 环境发现（本次适配的最大发现）：`/dev/shm` 写满会让 POSIX shm 以 SIGSEGV 静默失败

> **结论先行**：`ust-elf/test_ust_elf` 跑不完的**直接原因不是包、也不是平台映射缺陷，
> 而是本机 `/dev/shm`（tmpfs，1.0 GiB）**被写满**（Avail=0）。编排方 2026-10-18 预警
> 后复测确认。本节保留完整证据链，因为它揭示的是一个**错误掩盖机制**——空间耗尽在
> mmap 路径上表现为**不可捕获的 SIGSEGV**，而非 Linux 常规的 SIGBUS/ENOSPC。

### 6.1 环境读数（逐字）

```
$ df -h /dev/shm
Filesystem      Size Used Avail Use% Mounted on
tmpfs           1.0G 1.0G     0 100% /dev/shm

$ python3 -c "import shutil;print(shutil.disk_usage('/dev/shm'))"
usage(total=1073741824, used=1073741824, free=0)

$ ls /dev/shm
ls: /dev/shm: Permission denied          # 无法列举、无法自查占用者
```

### 6.2 机制：申请全绿、首次触碰即死

tmpfs 的 `ftruncate` 只改 i_size，页在**首次触碰时**才分配。于是申请链路全绿：

```
page_size=4096
shm_open fd=3 errno=2
ftruncate=0 errno=0
shm size=4096
mmap=0x5a2f720000 errno=0        ← mmap 成功，非 MAP_FAILED
Segmentation fault (core dumped) ← 首次读该映射，rc=139
```

**判据（把"空间"与"映射机制"分开）**：对同一对象的 fd 直写，错误码是可见的：

```
$ python3 -c "...os.write(fd, b'x'*4096)..."
write() FAILED: 28 ENOSPC [Errno 28] No space left on device
```

即**空间问题真实存在且可观测**，只是 mmap 路径把它吞掉了。

五组合全部 rc=139（`shm2.c`）：`MAP_SHARED`+`PROT_READ`(读)、`MAP_SHARED`+`RW`(读/写)、
`MAP_PRIVATE`+`PROT_READ`(读)、`MAP_PRIVATE`+`RW`(写)；加 `MAP_POPULATE` 也不改变
（`mmap` 仍成功、随后读仍 SIGSEGV）。

### 6.3 对照组：不是"映射坏了"，是"这个 tmpfs 没空间"

| 对照 | 探针 | 结果 |
|---|---|---|
| 匿名 `mmap(MAP_SHARED\|MAP_ANONYMOUS)` 读写 | `mm1.c` | rc=0 |
| 普通文件 `mmap(MAP_SHARED)` 读（页已存在） | `mm1.c` | rc=0 |
| `memfd_create()+ftruncate()+mmap()` 读写（内核内部 tmpfs） | `mm2.c` | rc=0 |
| `liburcu-bp` 注册/注销 + `call_rcu` + `nanosleep(3)` | `u3.c` | rc=0 |
| 不链接 lttng-ust 的 `sleep(3)`/`nanosleep(3)` | `s4.c`/`s6.c` | rc=0 |
| **链接 liblttng-ust 后只 `nanosleep(3)`** | `s5.c` | **rc=139** |

### 6.4 命中位置（root cause 定位链）

`liblttng-ust` 的构造函数创建了一个**把所有信号都屏蔽**的 detached 线程
（`lttng-ust-comm.c:1922-1934`：`sigfillset` + `pthread_sigmask(SIG_SETMASK, 全屏蔽)`
后才 `pthread_create`），该线程在 `wait_for_sessiond()`
（`liblttng-ust/lttng-ust-comm.c:1471`，
`uatomic_read((int32_t *) sock_info->wait_shm_mmap)`）读 shm 映射时 SIGSEGV。

定位方法：把该线程的信号屏蔽**临时解除**（诊断用，不随配方发布）后重编，
在 main 程序里用 `SA_SIGINFO` + `ucontext.uc_mcontext.pc` + `dladdr()` 打 PC：

```
SIGSEGV sig=11 addr=0x5b16a3c000 pc=liblttng-ust.so.0.0.0+0x33da4 lr=+0x31ea8
$ llvm-addr2line -e liblttng-ust.so.0.0.0 -f -C 0x33da4 0x31ea8
wait_for_sessiond   liblttng-ust/lttng-ust-comm.c:1471
wait_for_sessiond   liblttng-ust/lttng-ust-comm.c:1462
```

**为什么 SIGSEGV handler 收不到**：同步 SIGSEGV 在信号被屏蔽的线程里由内核
**直接按默认动作终止**。对照实验（`s7.c`/`s9.c`/`s10.c`）：同参数下 `*(int*)0=1`
的 handler 正常触发（rc=77），而链接 liblttng-ust 后的崩溃永远进不了 handler（rc=139）。

### 6.5 与"包"和"已有制品"的关系

把**完全相同的**消费者程序（只 `#include <lttng/tracef.h>` + `nanosleep(3)`）链接到
**已发布**的 `lttng-ust/2.15.1`（ohpcd 制品）→ **同样 rc=139**（连跑 4 次 4/4）。
⇒ 与本配方无关；也与 lttng-ust 版本无关；**是 `/dev/shm` 空间条件**。

### 6.6 处置（按环境失败，不按配方失败）

- 本包**不为此改任何配方内容**（与「内存耗尽 / 槽位不可用」同级的环境条件）。
- `ust-elf/test_ust_elf` 的 48 个测试点按 **NOT_RUN** 如实记录，原因写
  「环境：`/dev/shm` Avail=0」并附逐字读数（§6.1–6.3）。
- **可重跑性**：`/dev/shm` 恢复空间后，同一份提交应能取得该用例的干净读数。
  本执行体在会话期内无法清理 `/dev/shm`（`ls /dev/shm` 即 Permission denied，
  且属共享设备资源，按编排方口径不得自行处置）。
- 已沉淀知识：`knowledge/drafts/E4310-draft-8CAA.kv/.md`（写满 → SIGSEGV 掩盖 ENOSPC）。

## 7. 已知限制

1. **运行期（环境条件，非包缺陷）**：当 `/dev/shm`（全设备共享的 1 GiB tmpfs）
   写满时，任何链接 `liblttng-ust` 且存活超过约 1ms 的程序都会被 SIGSEGV 终止
   （机制见 §6）。`/dev/shm` 有空间时该路径正常（本机 `memfd`/匿名映射对照组
   全部 rc=0，且同一消费者程序链接已发布的 2.15.1 亦只在写满条件下崩溃）。
   **本会话期内 `/dev/shm` 已满且不可自查/清理**（`ls /dev/shm` → Permission denied），
   故运行期干净读数留待空间恢复后补取。
2. **依赖制品缺陷**：`liburcu/0.15.6` 包内 7 个 `.la` 的 `libdir='//lib'` +
   `dependency_libs` 含构建机私有前缀（`-L/…/usr/local/lib`）。配方侧已重写副本
   规避，依赖包本体未改 ⇒ 建议制品侧修复。
3. **sysroot 桩缺符号**：OHOS sysroot 的 `libc.so` 未导出
   `pthread_cancel`/`pthread_setcancelstate`，消费者若同时链接
   `liblttng-ust-tracepoint.so`，lld 的 `--no-allow-shlib-undefined` 会误报未定义
   ⇒ 需加 `-Wl,--allow-shlib-undefined`（test_package 已如此，并在 PR 正文说明）。
4. **上游小瑕疵（不影响本包）**：`include/lttng/ust-version.h` 生成
   `#define LTTNG_UST_VERSION 2.12.10`（**未加引号**），消费者无法把它当字符串
   使用（上游自身 0 处引用）。本包 test_package 只使用数值宏。

## 8. 未做 / 未发生项

- 未跑 `lttng-sessiond` 侧的真实会话（本仓库不含 lttng-tools；且平台 shm 缺陷
  已使 UST 域运行时路径不可用）。
- `tests/` 之外的 `doc/examples/` 样例只作 `make` 期编译覆盖（`all-local` 会编译
  8 个样例 + gen-tp），**不注册为 TESTS**，不计入 N；未单独统计其编译通过率。
- `liblttng-ust-java*` / `python-lttngust` 未启用（上游默认关闭；本任务范围外）。
- 未修改 `liburcu` 制品本体（按先例只做配方侧定位）。
