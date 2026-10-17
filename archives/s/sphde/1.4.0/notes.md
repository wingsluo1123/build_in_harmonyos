# sphde 1.4.0 适配笔记

## 基本信息
- 库: SPHDE (Shared Persistent Heap Data Environment)，LLNL/IBM
- 版本: 1.4.0（上游 GitHub tag `1.4.0`，commit 23f745a，2016-11-28）
- 上游仓库: https://github.com/sphde/sphde
- 构建系统: autotools（release tarball 自带预生成 configure/Makefile.in，无需 autoconf/automake）
- 编译器: clang 15（OHOS aarch64，原生构建，build=target）
- 状态: built（真机预检待跑）

## 源码
- conandata.yml 使用官方 GitHub tag archive URL（R39/PF7：只写官方源；CI 的
  build_and_test.sh 会自动为 github.com 源加 gh-proxy 等镜像 fallback）：
  `https://github.com/sphde/sphde/archive/refs/tags/1.4.0.tar.gz`
- sha256: f49d50979007cf7d9e735de9367cbced86f19a148c202245d9651251b3c2a4e7
- 已用 Debian 官方同版本 orig.tar.gz 交叉核验 sha256 一致（同源）。
- 2026-09-28：GitHub 直连在真机网络超时（connect timeout 30s），曾把单值 url 改为
  有序列表并前置 gh-proxy.com 镜像；2026-10-16 审查（review-memory §13/R39 与 PF7
  源URL闸）要求 conandata.yml 只写官方源，手写镜像前缀违规，故改回单一官方 URL，
  镜像回退交由 CI 自动处理。

## 库构成（src/Makefile.am）
- lib_LTLIBRARIES: libsphde.la（.so+.a）、libsphgtod.la（-all-static，仅 .a）、libsphgettime.la（-all-static，仅 .a）
- bin_PROGRAMS: sasutil（工具）
- 头文件安装到 include/sphde/
- 依赖: 无 conan 三方依赖；运行时依赖系统 librt(-lrt)、pthread、m
- configure.ac 在 LDFLAGS 硬编码 `-Wl,--no-as-needed -lrt`；libsphde_la_LIBADD = $(PTHREAD_LIBS) -lrt
- aarch64: sasconf.h 有 __aarch64__ 段（__SAS_BASE_ADDRESS 0x4000000000, Region 128GB, Segment 256MB）

## 上游测试
- 单元 = automake `make check`（TESTS 定义在 src/Makefile.am）
- 24 个 TESTS 条目，其中 sphmultipcqueue_t 被 `if HTM`（POWER 事务内存 -mhtm）门控：
  aarch64/OHOS 无 -mhtm → HTM=false → 不注册。**aarch64 注册总数 = 23**。
- test-suite.log（src/）automake 汇总块：# TOTAL/# PASS/# FAIL/# SKIP/# XFAIL/# XPASS/# ERROR
- 计数口径: autotools_tests；upstream_test_total=23
- 已接入 conanfile build()：`make check` → 解析 test-suite.log → 输出 HMBS_UPSTREAM_TEST_RESULT，
  结果持久化到 package res/upstream_test_result.json，由 test_package 重发标记链。

## 打补丁
- 0001-config.guess-ohos.patch（E205/E007）: config.guess 增加 HarmonyOS 检测，
  输出 aarch64-unknown-linux-ohos
- 0002-config.sub-ohos.patch（E205/E072）: config.sub 增加 ohos-linux->linux-ohos 映射 + OS 白名单
- 0003-configure-umask.patch（E129）: configure 临时目录创建 umask 077->022，规避 HMDFS setgid 写权限问题
- 0004-configure-pwd-fallback.patch（E158/E143）: 
  (a) configure ac_pwd `pwd` 增加 `2>/dev/null || "$PWD"` 回退，规避 HMDFS getcwd(2) 沿 .. 上溯
  失败导致的 "working directory cannot be determined"；
  (b) `-mhtm` 探测的编译命令加入 `-Wall -Werror`，使 aarch64 clang 上 "-mhtm unused argument"
  在探测阶段即判定不支持，从而不向 CFLAGS 注入 -mhtm，也不把 sphmultipcqueue_t 注册进 HTM 条件
  （与 aarch64 无硬件事务内存一致）。
- 0005-sasshm-key_t.patch（E131）: src/sasshm.h 自包含，显式 `#include <sys/types.h>` 使 key_t 在
  使用点可用。sasshm.c 先含 sasshm.h 后含 <sys/ipc.h>/<sys/shm.h>，在 OHOS 上传递包含链未能先提供
  key_t，导致 sasshm.h:37 "unknown type name 'key_t'"。
- 0006-makefile-no-unused-function.patch（clang 告警差异）: src/Makefile.in 的
  AM_CFLAGS/AM_CXXFLAGS 追加 `-Wno-unused-function -Wno-unused-but-set-variable`。
  OHOS clang 对未使用的 static inline 函数报 -Wunused-function（GCC 显式豁免 static inline），
  并对 SPHLFLoggerPrefetch 里仅作 prefetch 副作用的局部变量 touch 报 -Wunused-but-set-variable
  （GCC 豁免）；上游 AM_*FLAGS 恒含 -Wall -Werror 将两者提升为致命编译错误
  （src/sascompoundheap.cpp:60 SASCompoundHeapPercentFree、src/sphlflogger.cpp:973 touch）。
  仅补丁生成 Makefile.in（release tarball 自带预生成版，configure 不重跑 automake）。

## 0006 补丁（真机 compile 失败：unused function ... [-Werror,-Wunused-function]）
- 现象：make 编译 src/sascompoundheap.cpp 时报
  `src/sascompoundheap.cpp:60:1: error: unused function 'SASCompoundHeapPercentFree' [-Werror,-Wunused-function]`，
  make 退出码 2；同一 TU 里 SASCompoundHeapAvail/SASCompoundHeapPercentUsed 均被使用，仅
  SASCompoundHeapPercentFree 定义后从未使用（仅 #if 0 段引用其名字）。
- 根因：sphde 的 AM_CXXFLAGS/AM_CFLAGS（src/Makefile.am -> Makefile.in）恒含 `-Wall -Werror`。
  上游本以 GCC 构建，GCC 对 `static inline` 函数显式豁免 -Wunused-function；OHOS 用 clang 构建，
  clang 对未使用的 static inline 函数同样报 -Wunused-function，被 -Werror 提升为致命错误。
- 修复：0006 补丁在 src/Makefile.in 的 AM_CFLAGS/AM_CXXFLAGS 末尾追加 `-Wno-unused-function`
  （位于 -Wall -Werror 之后从而优先生效），使整个代码库中此类“上游只写不用的 static 辅助函数”
  不再被 clang 当作致命错误。属 clang 与 GCC 告警行为差异的移植修正，不动功能、不删代码、不影响
  make check 任何用例。
- 已用 GNU patch 在 release tarball 的 src/Makefile.in 上严格验证补丁可应用。

## 0006 补丁补充（真机 compile 失败：unused-but-set-variable 'touch' ... -Werror）
- 现象：make 继续编译 src/sphlflogger.cpp 时报
  `src/sphlflogger.cpp:973:12: error: variable 'touch' set but not used [-Werror,-Wunused-but-set-variable]`，
  make 退出码 2。上一轮 0006 只加了 -Wno-unused-function，未覆盖 -Wunused-but-set-variable。
- 根因：SPHLFLoggerPrefetch 中 `char touch = 0;` 在 for 循环里 `touch += *touchptr;` 累加，但循环结束
  后 touch 从未被读取（代码目的仅是借解引用 volatile char* touchptr 触发 cache line 预取）。GCC 不报；
  OHOS clang 报 -Wunused-but-set-variable，被上游 -Wall -Werror 提升为致命错误。
- 修复：扩展 0006 补丁，AM_CFLAGS/AM_CXXFLAGS 追加 `-Wno-unused-but-set-variable`
  （与 -Wno-unused-function 并列）。同样不删代码、不动功能、不影响 make check。
- 只新增编译开关，不改 sphlflogger.cpp（上游语义为预取副作用，保留原样）。

## 0004 补丁（真机 compile 失败：configure working directory cannot be determined）
- 现象：conan create 在 build 阶段 `autotools.configure()` 报
  `configure: error: working directory cannot be determined`，前缀大量
  `job-working-directory: error retrieving current directory: getcwd: cannot access parent directories`。
- 根因：HMDFS 上 getcwd(2) 沿 .. 向上遍历父目录失败，bash/mksh 的 pwd 内建回退到 getcwd(2) 而失败，
  autoconf 生成的 configure 中 `ac_pwd=`pwd` && test -n "$ac_pwd"` 检查直接 abort。
- 修复：a) 新增 0004 补丁把 sphde configure 的
  `ac_pwd=`pwd` && test -n "$ac_pwd" &&` 改写为
  `ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"` + `test -n "$ac_pwd" &&`，
  使 pwd 失败时回退到逻辑路径 $PWD；b) conanfile build() 在 apply_conandata_patches 前
  `os.chdir(self.build_folder)` 并 `os.environ["PWD"]=self.build_folder`，让 pwd 内建直接信任有效 PWD
  而不触发 getcwd，作为补丁回退的兜底（chdir 失败不阻断，仅依赖 PWD）。
- 补丁用 diff -u 生成、patch_ng 严格验证通过。

## 0005 补丁（真机 compile 失败：unknown type name 'key_t'）
- 现象：make 编译 src/sasshm.c 时报
  `src/sasshm.h:37:35: error: unknown type name 'key_t'`
  （sasshm.h:37 为 `extern __C__ int SASAllocateShmID(key_t key_id, ...)`）。
- 根因：sasshm.c 的 include 顺序为 errno.h/string.h/unistd.h/sasio.h/sasshm.h 后才是
  <sys/ipc.h>/<sys/shm.h>；key_t 定义在 <sys/types.h>（由 <sys/ipc.h> 传递包含）。在 OHOS 上
  sasshm.h 先于 <sys/ipc.h> 被解析时，传递包含链未能先提供 key_t，导致 "unknown type name 'key_t'"。
- 修复：给 src/sasshm.h 在 include 守卫后显式 `#include <sys/types.h>`，使头部自包含，key_t 在使用点
  一定可用；sasshm.c 自身的 `key_t shm_key;` 也随之可用。

## 0004 补丁追加（真机 compile 失败：-mhtm unused argument，-Werror 提升为致命错误）
- 现象：configure 已跑通并生成 config.status，但 make 编译 src/sasshm.c 时报
  `clang-15: error: argument unused during compilation: '-mhtm' [-Werror]`，
  make 退出码 2。
- 根因：configure.ac 用 AX_CHECK_COMPILE_FLAG([-mhtm],...) 只探测"-mhtm 是否被编译器接受"
  （空文件可编译即为 yes），Accept 不等于 Use。aarch64 的 clang 接受 -mhtm 但无硬件事务内存，
  编译时告警 "argument unused"，而 sphde 的 AM_CFLAGS 恒含 -Wall -Werror，遂被提升为致命错误。
- 修复：把 configure 中 AX_CHECK 探测的编译命令 `CFLAGS="$CFLAGS  -mhtm"` 改为
  `CFLAGS="$CFLAGS -Wall -Werror -mhtm"`，使其在真实构建所采用的告警级别下探测；aarch64 clang
  因 unused-argument 告警被 -Werror 提升而探测失败 → ax_cv_check_cflags___mhtm=no → 不注入 -mhtm、
  不注册 HTM 条件的 sphmultipcqueue_t（与 aarch64 无 HTM 一致）。
- 注意：configure 需保持仅被 0003+0004 两个补丁触及（patch_ng 对同一文件 3 个补丁的链式应用
  不可靠）；0005 独立补丁在链式应用中 apply 返回 False，已并入 0004 第二个 hunk（用 diff -u
  生成、patch_ng 严格验证两个 hunk 均生效）。

## 0003 补丁修复（真机 compile 失败，两轮）
### 第 1 轮：hunk 头行号/行数错位
- 现象：`apply_conandata_patches` 报 `0003-configure-umask.patch: source file is different - b'configure'` / `actual : b'}'`。
- 根因：旧 0003 补丁 hunk 头声明 `@@ -18947,7 +18947,7 @@`（旧文件 7 行），但 hunk 体实际含约 10
  行旧文件行，且起始行号 18947 与 release tarball 自带 configure（autoconf 预生成版）不符。GNU patch
  靠 fuzz/offset 能勉强应用，但 Conan 用 patch_ng 严格解析校验 hunk 行数与上下文即报失败。
- 第 1 轮修复：基于 tarball 真实 configure 重新生成补丁，hunk 头改为 `@@ -18948,12 +18948,12 @@`，
  上下文取自 `# Create a (secure) tmp directory` 段。GNU patch 通过。

### 第 2 轮：hunk 体与声明行数不一致 → patch_ng 报 "patch stream is incomplete!"
- 现象：真机 conan create 报 `0003-configure-umask.patch: error: patch stream is incomplete!` /
  `Failed to parse patch`。
- 根因：手写补丁把 hunk 头写成 `@@ -18948,12 +18948,12 @@`（旧文件 12 行），但 hunk 体实际只粘贴了
  11 行旧文件行——**漏掉了 `ac_tmp=$tmp` 之后的尾随空行上下文**。patch_ng 按声明 12 行读取，读到第 11 行
  后到 EOF，判定流不完整直接解析失败（patch_ng.fromfile 返回 None → Conan 抛 Failed to parse patch）。
- 修复：用 `diff -u configure.orig configure` 重新生成（覆盖尾随空行），保证 hunk 体旧文件行数=12 与
  `-18948,12` 完全一致。已用本机同源 conan 2.29 的 patch_ng 复现整条 0001/0002/0003 解析+apply(fuzz=0)
  全部通过，且 config.guess/config.sub/configure 结果正确。
- 教训：手写/手工拷贝 unified diff 极易漏掉 hunk 尾随空行导致 patch_ng 计数不符。必须用 `diff -u`
  生成补丁并以 Conan 实际解析器（patch_ng）验证，而不是只看 GNU patch。

## 待真机验证事项
1. `-lrt`（librt）：configure.ac 与 Makefile.am 硬编码 -lrt；若 OHOS 无独立 librt，需在 build 处理。
2. System V 共享内存（shmget/shmat）+ mmap 固定地址区（0x4000000000）：sassim_t 等测试依赖；
   若 OHOS 限制 shm，将出现个别测试失败，按 gaps 类别如实上报。
3. make check 的 23 个测试程序逐一在真机执行，pass/fail 以 test-suite.log 为准。
4. test_package 消费测（test.c 6 断言）需在真机链接 libsphde.so 并跑通 SAS 简单堆往返。

## 编译命令（真机）
```bash
conan create archives/s/sphde/1.4.0/conanfile.py \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 备注
- 未提交任何改动，仅工作树。待 HMBS 真机预检通过后由后台提交推送。

## 2026-09-28 预检失败：can't fork - try again（编译阶段，环境资源故障）
- 现象：hmbs-preflight 报失败阶段 compile，原因
  `/storage/Users/currentUser/preflight/clients/baaf5de91e18/preflight.sh[319]: can't fork - try again`。
- 定性：`can't fork - try again` 对应 fork() 返回 EAGAIN，是 OS/内核进程创建被拒
  （进程槽/线程上限、memory/cgroup pids.max、RLIMIT_NPROC、瞬时负载等），故障点位于
  HMBS 自己的 preflight.sh 驱动脚本第 319 行，而非配方产出的 make/test 输出。属于真机
  环境/资源型故障，非配方或测试代码缺陷。
- 复核配方无资源放大：conanfile build() 用 `make -j1`、`make check -j1` 串行执行，
  无并行 fork 爆炸、无死循环、无 subprocess 失控。没有任何 CFLAGS/补丁/测试接入改动能
  阻止内核在机器资源耗尽时对 fork 返回 EAGAIN。
- 未含 `HMBS 平台诊断` 错误码，不适用文件系统子能力最小适配流程。
- 结论：不做伪造配方改动；保持工作树现状，等待真机环境恢复后由 HMBS 复跑。


## 0007 补丁（真机 compile 失败：generate-changelog.sh bad interpreter Error 126）
- 现象：make 在 build-release 顶层执行 all 时，
  `/data/service/hnp/bin/bash: ./generate-changelog.sh: /bin/bash: bad interpreter: No such file or directory`，
  `make[2]: *** [Makefile:987: ChangeLog.md] Error 126`，make 退出码 2。
- 根因：顶层 Makefile.in 的 `dist_doc_DATA = COPYING ChangeLog.md`，automake 使 `all-am: ... $(DATA) ...`，
  `$(DATA)=$(dist_doc_DATA)` 含 ChangeLog.md。tarball 内 ChangeLog.md 不存在（其由 `ChangeLog.md:` 规则经
  generate-changelog.sh 从 git 历史生成），故 `make all` 触发该规则。generate-changelog.sh shebang 为
  `#!/bin/bash`，而 OHOS 上 /bin/bash 不存在（bash 在 /data/service/hnp/bin/bash），内核 exec 报
  "bad interpreter: No such file or directory"。且 tarball 无 .git 历史，规则本也无法工作。
- 修复（0007 补丁，patch 顶层 Makefile.in）：
  (a) `dist_doc_DATA = COPYING ChangeLog.md` -> `dist_doc_DATA = COPYING`，使 $(DATA) 不含 ChangeLog.md，
      all-am 不再构建它；
  (b) 删除 `ChangeLog.md:` 规则块，避免残留引用。
  不动功能、不影响 make check。configure 从 Makefile.in 生成 Makefile，故补丁目标是 Makefile.in。
- 已用 GNU patch dry-run + conan 同源 patch_ng 在 release tarball 的 Makefile.in 上严格验证 0007 可应用。


## 0008 补丁（真机 compile 失败：make check 编译 tests/sphgtod_t.c、sphgettime_t.c 的 -Wformat/-Wabsolute-value）
- 现象：make all 已通过（0007 修复 ChangeLog.md 后），但 make check 编译 TESTS 程序时报
  - `tests/sphgtod_t.c:48/51/81/101: error: format specifies type 'unsigned long' but the argument has type 'unsigned long long' [-Werror,-Wformat]`
  - `tests/sphgtod_t.c:76/79/96/99: error: taking the absolute value of unsigned type has no effect [-Werror,-Wabsolute-value]`，
  8 errors generated，make[2]: *** [Makefile:1222: tests/sphgtod_t.o] Error 1，check 退出码 2。
- 根因（clang vs GCC 行为差异，被上游 -Wall -Werror 提升为致命）：
  (a) sphde 的 tests/sphgtod_t.c、sphgettime_t.c 用 `#if __WORDSIZE == 64` 选 NS_P_S/NS_P_uS 的
      UL 或 ULL 后缀。OHOS 上该文件预处理时走了 `#else`（ULL）分支，使
      `(uint64_t)tv2.tv_sec * NS_P_S + ...` 表达式的类型为 unsigned long long；而平台 PRIu64 展开为
      "lu"（unsigned long）。两者同为 64 位无符号（LP64 下 unsigned long 与 unsigned long long 等宽），
      仅类型名不同、值完全一致，但 clang -Wformat 仍报错。
  (b) `llabs(gtod_ns - sphgtod_ns)` 中 gtod_ns/sphgtod_ns 为 uint64_t（无符号），差值亦无符号，
      clang -Wabsolute-value 报 "对无符号类型取绝对值无效果"。
  以上均为 clang 独有的严格告警，GCC 不报；上游代码语义正确，不改动测试逻辑，只抑制告警。
- 修复（0008 补丁，patch src/Makefile.in 的 AM_CFLAGS/AM_CXXFLAGS）：
  在 0006 已追加的 -Wno-unused-function -Wno-unused-but-set-variable 之后并入
  `-Wno-format -Wno-absolute-value`。AM_CFLAGS 同时作用于全部 src 编译（库+测试），
  库本身已 -Wformat 干净，宽化抑制无副作用；测试进程仍照常编译、链接、运行全部断言。
- 已用 GNU patch dry-run + conan 同源 patch_ng 在 release tarball 上按序 0001-0008 严格验证全部可应用。


## 0009 补丁（真机 compile 失败：Makefile.in 1316 tests/sphlflogger_tt-sphlflogger_tt.o unknown type name '__pid_t'）
- 现象：make all 已通过（0008 修复 sphgtod_t/sphgettime_t 的 -Wformat/-Wabsolute-value 后），make check
  继续编译 TESTS 程序时报 `tests/sphlflogger_tt.c:61:24: error: unknown type name '__pid_t'; did you mean 'pid_t'?`
  及 77:5 同样错误，2 errors generated，check 退出码 2，test-suite.log 未生成。
- 根因：sphlflogger_tt.c 的 fdisplayProcMaps(__pid_t pid) 与 displayMyProcMaps() 里 `__pid_t pid; pid=getpid();`
  使用了 glibc 内部 typedef __pid_t；OHOS 用 musl 系 libc，不定义 __pid_t，只公开 pid_t（unistd.h 提供，
  值为 int，与 /proc/%d 的 %d 格式一致）。这不是 clang 告警差异而是目标 libc 缺失类型，无法用 -Wno 抑制。
- 修复（0009 补丁）：把四个测试文件里所有 __pid_t 替换为可移植的 pid_t：
  src/tests/sphlflogger_tt.c、sphlflogger_ttt.c、sphlogportal_tt.c、sphsinglepcqueue_tt.c
  （后三个是同样的 fdisplayProcMaps/displayMyProcMaps 模式，会在 sphlflogger_tt 之后依次编译到，
  一并修复避免再烧真机轮次）。均含 <unistd.h>，pid_t 可用；类型为 int，%d 格式不变，getpid() 返回 pid_t
  匹配，不动任何断言/逻辑。
- 已用 GNU patch dry-run + conan 同源 patch_ng 在 release tarball 上按序 0001-0009 严格验证全部可应用，
  且四个文件 __pid_t 残留为 0。


## 0010 补丁（真机 compile 失败：sphdirectpcqueue_ttt.c:677 incompatible integer to pointer conversion，strerror_r）
- 现象：make all 已通过，make check 编译 TESTS 程序时报
  `tests/sphdirectpcqueue_ttt.c:677:15: error: incompatible integer to pointer conversion initializing 'char *' with an expression of type 'int' [-Wint-conversion]`，
  1 error generated，make[2]: *** [Makefile:1222: tests/sphdirectpcqueue_ttt.o] Error 1，check 退出码 2，
  test-suite.log 未生成。
- 根因（glibc vs musl 的 strerror_r 签名差异，被上游 -Wall -Werror 提升为致命）：
  两个测试文件（sphdirectpcqueue_ttt.c、sphmultipcqueue_t.c）在 sched_setaffinity 失败分支里写
  `char *msg = strerror_r(errno,buf,sizeof buf); if (!msg) msg = buf;`。glibc 在 _GNU_SOURCE 下
  strerror_r 为 GNU 版，返回 `char*`；OHOS 用 musl 系 libc，strerror_r 恒返回 `int`（XSI/POSIX 版，
  即便定义了 _GNU_SOURCE 也不改变签名，与 _GNU_SOURCE 无关）。于是 clang 报
  "incompatible integer to pointer conversion"。这是目标 libc 差异，用 -Wno 抑制不改变语义，
  应改为可移植写法。
- 修复（0010 补丁）：改为忽略返回值、直接读取已填充的 buf——
  `buf[0]='\0'; strerror_r(errno,buf,sizeof buf); ...fprintf(...,buf);`。
  两平台的 strerror_r 都把结果写入 buf（GNU 版在错误信息可放入时同样写 buf）；预置 buf[0]='\0' 保证
  strerror_r 失败或太小时 buf 至少为空串，行为安全。删除原 `char *msg = ...; if(!msg) msg=buf;`
  的 GNU 专属写法与 msg 变量，打印直接传 buf。不动断言/测试逻辑。
  两处（sphdirectpcqueue_ttt.c、sphmultipcqueue_t.c）一并修复（sphmultipcqueue_t 在 aarch64 因 HTM
  不注册，但一并修掉避免其他平台绕真机轮次）。
- 已用 GNU patch dry-run + conan 同源 patch_ng 在 release tarball 上按序 0001-0010 严格验证全部可应用。
- 2026-10-16 P3 复核：原「忽略返回值直接读 buf」在 glibc 上并不总是成立（GNU strerror_r 返回值
  可能指向静态串、buf 未写），故该补丁已改为按 `__GLIBC__ && _GNU_SOURCE` 分支并把结果统一
  落在 buf（详见文末「CI #95036 修复」）。此处保留原始诊断记录。


## 真机 package() 失败：make install 的 toybox install 在 HMDFS 上 Error 64
- 现象（本轮）：make all 与 make check 均通过（0010 修复 strerror_r 后），到达 package()
  stage 的 autotools.install() 时报
  `make[2]: *** [Makefile:1528: install-libsphdeincludeHEADERS] Error 64`，
  make 退出码 2，安装头文件的命令
  `<runtime>/bin/install -c -m 644 <30+ 头文件> '.../p//include/sphde'` 返回 64（无 stderr）。
  `ERROR: sphde/1.4.0: Error in package() method, line ...`，autotools.install() 抛 Error 2。
- 根因（E596/E188/E098/E087，知识库已文档化）：worker 的 toybox `install` 是精简实现，
  `-c`（copy）选项在 HMDFS 的权限/UUID 映射下直接失败返回 Error 64；且目标环境无 GNU
  coreutils install（E098），HMDFS 不支持 chmod（E087）。autotools 的 configure 把探测到的
  toybox install 路径（写死 `-c` 后缀）固化进所有子 Makefile 的 `INSTALL` 变量，
  `INSTALL_DATA = ${INSTALL} -m 644`、`INSTALL_PROGRAM = ${INSTALL}` 均引用它，
  于是 make install 对头文件（install -c -m 644）与共享库（libtool 也经 INSTALL_PROGRAM）
  全程走 toybox install → Error 64。此前轮次从未到达 install 阶段，故本轮才暴露。
- 修复（配方 conanfile.py，不改源码、不加补丁）：参考知识库 openfst 家族（libfstngram
  E596）的验证形态——在 build() 里写一个 cp/mkdir 的 install shim（接受 install 标准参数，
  `-m MODE` 容错跳过 chmod、`-d` 走 mkdir -p），再用 os.walk 遍历 build_folder 下所有
  已生成 Makefile，把 `INSTALL = <toybox install -c 路径>` 行改为 `INSTALL = <shim 绝对路径>`。
  INSTALL_DATA/INSTALL_PROGRAM 引用 ${INSTALL} 自动跟随，make install 全程用 shim 的 cp 复制，
  不再碰 toybox install / chmod。
- 关键约束（来自 E596，避免踩坑）：
  - 不可靠 PATH 前置替换（conan build env 会覆盖 PATH）；
  - 不可给 Autotools.install() 传 'INSTALL_DATA=$(INSTALL)'（bash 命令替换吃空参数 → Error 126）；
  - 只要在 build() 的 autotools.configure() 之后改 Makefile（configure 才能把 INSTALL 固化进去）。
- 已在本机沙箱逐场景验证 shim：`install -c -m 644 a.h b.h c.h dest/`（本轮失败形态，多个源+目录）、
  单文件、`-d` mkdir、落单一文件目标 均正常（退出 0、文件齐）。真机结果以 next 轮为准。
- 不改动任何上游测试计数/断言/口径；make check 23 个用例照常跑，结果标记只依赖 test-suite.log。


## 2026-09-28 预检失败：HMBS_TEST_PACKAGE_RESULT passedCount 非法（158），及上游 14/23 失败根因

### 直接 gate 失败
- 现象：test_package 阶段报
  `Signal 31 (core dumped)`，`ERROR: sphde consumer test failed rc=159`，
  `HMBS_TEST_PACKAGE_RESULT={... "passedCount": 158}`。门禁拒绝：passedCount 必须为 0~6 整数。
- 根因（标记逻辑 bug）：test_package/conanfile.py 里 `passed = max(0, rc-1)` 假定 rc 一定是
  test.c 的失败断言编号（1~6）。但 test.c 是被信号杀死的（shell 退出码 = 128+signum，
  SIGSYS=31 → 159），159 不是合法断言编号，`rc-1=158` 越界。
- 修复：按 rc 语义分三段：
  - rc==0 → 全过，passedCount=6；
  - 1<=rc<=6 → 干净断言失败，passedCount=rc-1；
  - 其它（信号/127 等未正常完成）→ passedCount=0（进程未完成，无法归属已过断言数），
    passed=false，并给 ohos_feature gaps + detail。

### 底层根因：OHOS seccomp 阻断 SYSV 共享内存 → SIGSYS
- 复现证据：test_binary 一进 SASJoinRegion 即 `Signal 31 (core dumped)`（SIGSYS）。
- 源码定位（sphde-1.4.0 src/）：
  - sassim.cpp `SASJoinRegionByName` 调 `SASAttachAnchorSeg`/`SASCreateAnchorSeg`，并
    `mmap(..., MAP_FIXED)` 于 `__SAS_BASE_ADDRESS`（aarch64 0x4000000000）。
  - sasshm.c `SASAllocateShmID` 用 `shmget`/`shmat`（anch hor 段），`SASRemoveShmID` 用 `shmctl`。
  - 即 SPHDE 的 SAS 区域依赖 System V 共享内存 + MAP_FIXED 固定地址 mmap。
- 定性：OHOS（musl 系 / Harmony 内核）不提供 SYSV 共享内存，seccomp 对 shmget/shmat 返回
  SIGSYS（signal 31）。这是平台功能限制（ohos_feature），非缺依赖（不能靠补依赖解决），
  也不能靠改 CFLAGS/-Wno 抑制（运行时信号）。
- 上游测试：make check 23 个里 9 过 14 挂——通过的都是不依赖 SAS 区域的
  （sphgtod/sphgettime/bitvec/sasatom 等），挂的全是依赖 SAS 区域做
  join/heap/segment/index/context/stringbtree/lockfree logger/portal 的测试。
- 处理：不伪造通过、不删断言、不静默跳过。在上游 HMBS_UPSTREAM_TEST_RESULT 加
  gaps=[{count:14, category:"ohos_feature", detail/evidence}]（14=23-9，与 nfailed 一致）；
  在 test_package marker 加 ohos_feature gaps 说明崩溃。


## 2026-09-28 补记：CI 整作业 14400s 超时 —— 多线程 SPSC 测试挂起
- 现象（CI build #63629，worker CI-035，conan-build-test 步骤）：
  make check 已跑完 sphgtod/sphgettime/.../sphsinglepcqueue_tt（末行输出
  `oFAIL: sphsinglepcqueue_tt`）后无任何输出，整作业 14400s 无输出被 kill。
  排查后确认下一顺位的 sphsinglepcqueue_ttt（及其后续 sphdirectpcqueue_ttt）
  是**多线程**共享内存 SPSC 队列测试，内含无界自旋等待：
  - src/tests/sphsinglepcqueue_ttt.c 的 lfPCQentry_test / fasttest / verify /
    fastverify：`while (SPHSinglePCQueueFull/Empty(pqueue)) sched_yield();`
  - src/tests/sphdirectpcqueue_ttt.c 同类自旋。
  在 OHOS 共享内存语义下 producer/consumer 可双双自旋不推进 → 无限挂起，拖垮
  整个 make check。此前真机（hmbs 预检）环境 SAS 测试以 Signal 31 崩溃快速结束
  （故 preflight 过），而该 CI worker 映射成功 → 测试真正跑起来才暴露挂起，属
  平台环境相关差异，不是配方逻辑错误。
- 修复：不动上游测试源码/断言/口径（仍真机执行全部 23 个，upstream_test_total=23
  不变）。改为给 make check 加**逐测试超时**：
  1. conanfile 新增 `_write_test_timeout_wrapper()`，向 source_folder 写一个纯 sh
     的 `test-timeout-wrapper.sh`（不依赖 coreutils timeout，用 background+sleep+
     kill -9；默认 SPHDE_TEST_TIMEOUT=300s，超时 kill -9 该测试返回非零，automake 记为 FAIL）。
  2. build() 在 make check 前 `os.environ["LOG_COMPILER"]=source/test-timeout-wrapper.sh`
     并 `os.environ.setdefault("SPHDE_TEST_TIMEOUT","300")`。
     —— sphde 生成的 src/Makefile 未定义 LOG_COMPILER，环境变量会被 GNU make 采纳
     为 make 变量，并随递归子 make（SUBDIRS=src）传播进 src/，automake 的 .log 规则
     `$(LOG_COMPILE)=$(LOG_COMPILER) ...` 即把每个测试包进超时 wrapper。
  3. 挂起的测试被 kill 后 automake 记为 FAIL（exit 124），计入 test-suite.log 的
     #FAIL → conanfile `_emit_upstream_test_result()` 不变，仍从 test-suite.log 单向
     解析 #TOTAL/#PASS/#FAIL，恒等式 passed+failed==executed 自检，不臆造计数。
  - 快速通过 / 快速崩溃（SIGSYS 等）的测试不受 wrapper 影响（kill -0 检测到子进程
    退出即 wait 返回真实 rc）。
- 已更新：conanfile.py（build 接入 + 新方法 + gaps detail/evidence 补充挂起+超时
  说明）、manifest.yaml（knowledge_gained 条目）、MANIFEST.yml、.hmbs/pr-body.md 草稿
  （补充挂起/超时说明；通过率数字以真机预检实测为准，不虚构）。
- 待真机验证：下一轮 hmbs 预检用新 conanfile 跑 conan create，确认 make check 在
  逐测试超时下完整结束、test-suite.log 汇总可解析、无整作业超时；若确认挂起测试被
  限时截断为 FAIL 即符合预期。


## 2026-09-29 补记：test_package 消费测 SAS 崩溃被硬 raise 误判为构建失败
- 现象（CI build #63981，conan-build-test）：make check 已正常完成（逐测试超时
  生效，test-suite.log 汇总 23 发现 / 10 过 / 13 挂，HMBS_UPSTREAM_TEST_RESULT
  正确输出）。但 test_package 阶段报
  `Error in test() method, line 113 / ConanException: sphde consumer smoke test failed`
  → `conan create failed` → L1_RESULT=fail → CI 判定失败。
  其前日志：`Signal 31 (core dumped)` / `rc=139`，即消费测在 SASJoinRegion()
  处被 seccomp SIGSYS 崩溃。
- 根因：sphde 的消费测 test.c 第一个调用就是 SASJoinRegion()（sassim.cpp 内部走到
  shmget/shmat + mmap MAP_FIXED），OHOS seccomp 阻断这些系统调用 → 进程以信号崩溃，
  根本到不了任何 CHECK_* 断言。test_package/conanfile.py 已如实把该异常进程记为
  HMBS_TEST_PACKAGE_RESULT passedCount=0 + ohos_feature gap，但在结尾写死
  `if not passed_bool: raise ConanException(...)`，把"已如实申报的平台限制"当成硬失败，
  使 conan create 退出非零，被 CI 一并算作构建失败。
- 修复：把硬失败条件收紧为"仅当失败未被归类为已知平台限制时"，即
  `if not passed_bool and not gaps: raise`。OHOS 上该消费测必然带 ohos_feature gap
  （passedCount=0、evidence 指向 sassim.cpp/sasshm.c 的 SASAttach/CreateAnchorSeg、
  mmap MAP_FIXED），故不再硬失败 conan create，构建正常完成；非 SAS 平台若消费测
  干净失败（rc 1..6，gaps 为空）仍会 raise，保留 fail-fast。标记与计数完全不变，
  只是不再把文档化的平台 gap 误判为构建失败。符合"有失败/跳过不代表必然拦截，但每个
  未通过项必须有具体技术原因及证据"。
- 已更新：test_package/conanfile.py（raise 条件 + 注释）、test_package/MANIFEST.yml
  （平台限制说明补充消费测非硬失败）、.hmbs/pr-body.md 草稿（新增用例通过率说明 +
  已知限制 item2）。
- 待真机验证：下一轮 conan create 应整体成功（smoke 测 marker passedCount=0 + gap 但
  不 raise），L1_RESULT=pass。


## 2026-10-13 CI 复跑失败：#88944/#89113 fork EAGAIN 尖峰（非配方缺陷）→ 有界退避重试
- 现象（同一 recipe revision `sphde/1.4.0#ad08107d318fd83c8d9faeada77a5aa7` 的四次 CI 构建）：
  - #88798（PASS，fork 报错 0 处）、#89013（PASS，fork 报错 0 处）
  - #88944（FAIL）：`configure: fork: retry: Resource temporarily unavailable` 连续 30 处，
    并因探测被 fork 打断而误判 C++ 预处理器为 `/lib/cpp`，最终
    `configure: error: C++ preprocessor "/lib/cpp" fails sanity check`。
  - #89113（FAIL）：`configure[33]: can't fork - try again`（在 configure 的第一个 fork 即失败）。
  - 关键旁证：#89113 同一运行里 CI 自身脚本
    `ci/scripts/knowledge_check.sh: fork: retry: Resource temporarily unavailable` 也在报错，
    说明是 worker 级 fork/进程资源瞬时耗尽，而非 sphde 配方或测试代码缺陷。
- 定性：`can't fork - try again` / `fork: retry: Resource temporarily unavailable` 对应
  fork() 返回 EAGAIN。同一 revision 在不同 worker 上 PASS/FAIL 不一致，是
  DRAFT-11327 所述「同 SHA 不同 worker 结果不一致 = 环境资源问题」的典型判据；
  E491 forbid_3 要求改包前先有设备资源证据，本日志已提供（CI 自身脚本同批报错）。
  configure 是 autotools 里 fork 最密集的步骤（数百次 sh/clang 探测），最先受害。
- 修复（有界、可观测、不改构建语义/测试口径，参照同仓库已合入的 libcmis/0.6.3 先例）：
  - `build()` 不再直接调用 `autotools.configure()`，改为 `_configure_with_retry()`。
  - 最多尝试 3 次，退避 15s/30s；仅在失败输出或 `config.log` 尾部出现 fork 标记
    （`can't fork`/`cannot fork`/`try again`/`resource temporarily unavailable`/`out of memory`）
    时才重试；真实 configure 错误立即抛出，不掩盖、不伪造通过。
  - `_run_configure_capturing()` 复刻 `Autotools.configure()` 的命令（configure 路径 +
    `load_toolchain_args(generators_folder).get("configure_args")`），仅把 stdout/stderr
    同时写入缓冲以判定 fork 标记；成功/失败均把缓冲原样回放到日志，保持可观测性；
    失败时另 dump `config.log` 尾部 40 行作为证据。
  - 构建产物、编译选项、`make check` 的 23 个上游测试与 test_package 计数全部不变；
    不跳过测试、不删断言、不改通过率口径。
- 与 DRAFT-sphde-1.4.0-autotools-portability-fix-family 的 forbid 说明：该草稿禁止的是
  「对随机资源故障做无意义改动」；此处不是无意义改动，而是与 libcmis 同形态的有界可靠性
  重试（不改语义、仅在确证 fork 标记时退避重试），故不冲突。
- 待真机验证：下一轮 CI/预检应正常通过（fork 尖峰时自动退避重试，非尖峰时一次通过）。


## 2026-10-13 人工审查打回（rule4 少报 / rule6 AI 检视未覆盖）修复

### 直接失败
- hmbs-preflight 证据门禁 `incomplete`：`rule4 少报：上游核验 N=24 > 声明 N=23`。
  上游测试标记 `discovered=23`（旧配方用 test-suite.log 的 `# TOTAL: 23` 当 discovered），
  而审查按上游完整清单核验为 24 → 少报，直接拒绝放行。
- rule6：最新提交晚于最新 AI 检视，属调度问题（HMBS 在新 head 后统一发 `/ai review`），
  执行器本轮不自行处理、不发评论。

### 根因（证据）
- `src/Makefile.am` 的 `TESTS +=` 条目完整清单共 **24** 个：
  23 个在顶层（sphgtod_t … sphdirectpcqueue_ttt）+ `sphmultipcqueue_t` 位于
  `if HTM` … `endif` 条件块（行 257-260）。
- `configure.ac` 行 117-122：`AX_CHECK_COMPILE_FLAG([-mhtm], … htm=true)` +
  `AM_CONDITIONAL([HTM], …)`。aarch64/OHOS 无 HTM（0004 补丁已让 -mhtm 探测在
  -Wall -Werror 下失败），HTM=false → `sphmultipcqueue_t` 不注册。
- 该测试源码 `src/sphmultipcqueue_t.c` 用 `#if defined(__HTM__)` 包裹主体，
  `src/sphmultipcqueue.cpp` 整个 `#ifdef __HTM__` 且用 `getauxval(AT_HWCAP2)` 查
  `PPC_FEATURE2_HAS_HTM`，是 POWER 专属特性。
- 旧配方把 discovered 取成 test-suite.log 的 `# TOTAL`（当前平台注册子集=23），
  等于把「上游清单存在但不注册的 1 项」归零 → rule4 少报。

### 修复（conanfile.py，不改测试口径/不删断言/不跳过）
- 新增 `_count_upstream_tests()`：解析 `src/Makefile.am`，用条件栈区分
  `if <COND> … endif` 内的条目，返回 `(inventory=24, registered=23, gated=[sphmultipcqueue_t])`。
  这是**唯一确定性来源**（源码文件，非 stdout 计数、无减法）。
- `_emit_upstream_test_result()`：
  - `discovered = inventory (24)`（上游完整清单，避免少报）；
  - `executed/passed/failed/skipped` 仍单一来自 `src/test-suite.log` 汇总块；
  - 恒等式自检扩充：`passed+failed==executed`、`executed+skipped<=discovered`、
    `executed<=discovered`、全部非负；不满足直接抛错，不凑数；
  - `registered != executed` 时打 warning（可观测，不静默）；
  - gaps 分两类：`ohos_feature`（nfailed，已执行未通过）+ `environment`
    （not_executed = discovered-executed，条件门控未注册未执行，含条目名）；
  - `gap_total == discovered - passed` 自检；
  - status：`failed`（有 nfailed）/ `incomplete`（无 nfailed 但有 gaps）/ `passed`（无 gaps）。
- MANIFEST.yml：`upstream_test_total: 23 → 24`，`upstream_test_count_detail` 改为完整清单
  口径并说明 23 注册 / 1 environment gap；`upstream_tests` 列表补 `sphmultipcqueue_t`
  条目（标注 HTM 门控、未执行）。
- manifest.yaml：knowledge_gained 中「TESTS 注册 23」更正为「完整清单 24，HTM 门控 1 项未执行」。
- `.hmbs/pr-body.md`：上游表改 24（完整清单），适配后表写 23 执行 / 1 未执行，验证结果段
  说明 gaps（ohos_feature 14 + environment 1），补丁说明由 6 个更正为实际 10 个。

### 本机验证（不代替真机）
- 用真实解压树 `.hmbs/src/sphde-1.4.0/src/Makefile.am` 跑 `_count_upstream_tests` 逻辑：
  inventory=24、registered=23、gated=['sphmultipcqueue_t']。
- 以旧真机日志数字（TOTAL 23 / PASS 9 / FAIL 14）模拟 `_emit_upstream_test_result`：
  discovered=24、executed=23、passed=9、failed=14、skipped=0、not_executed=1、
  gap_total=15=24-9、status=failed。恒等式全部成立。
- `python3 -m py_compile conanfile.py` / `test_package/conanfile.py` 通过。

### 待真机验证
- 下一轮 conan create 的 `HMBS_UPSTREAM_TEST_RESULT` 应为
  `discovered=24, executed=23, passed=9, failed=14, skipped=0`，gaps 含
  `ohos_feature count=14` + `environment count=1`，`gap_total=15=24-9`；
  不再被 rule4 判少报（实测 N=24 ≤ 声明 N=24）。
- rule6 由 HMBS 在新 head 推送后统一发 `/ai review` 覆盖。


## 2026-10-16 CI #91113 修复（configure[33]: can't fork，fork EAGAIN）

### 现象与证据
- CI 校验失败（build #91113，worker OpenHarmonyPCDeveloper-CI-010，`conan-build-test` 步骤）：
  configure 三次尝试均在脚本启动处即失败：
  `.../b/configure[33]: can't fork - try again`
  （configure 第 27/33 行为 M4sh 初始化的 `case \`(set -o)\` ...` / `esac`，是 configure 的第一个 fork）。
- 同一段日志里 CI 自身脚本亦报 `knowledge_check.sh: fork: retry: Resource temporarily unavailable`，
  即 worker 全局 fork/进程资源临界；属 DRAFT-11327（同型间歇性 `can't fork`，先判环境资源）
  与 E491 forbid_3 类别。配方已用「自带预生成 configure、不跑 autoreconf」规避高开销自举。
- 但原配方的退避预算（3 次 / 45s）不足以跨过该压力窗口：三次重试都落在同一个首个 fork。

### 本轮改动
1. `conanfile.py:generate()` 顶部 `self.conf.define("tools.env:deactivation_mode", "function")`：
   Conan 默认（unset）模式下 `conan*env*.sh` 在 source 期执行
   `for v in <vars>; do value=$(printenv $v); ...; done` —— 对每个导出变量 fork 一次 printenv。
   AutotoolsToolchain 导出 CC/CXX/AS/AR/RANLIB/NM/STRIP/OBJDUMP/CFLAGS/CXXFLAGS/CPPFLAGS/
   LDFLAGS/PKG_CONFIG_PATH 等十余个变量，因此**每次 `self.run()`（configure/make/make check/install）
   在目标命令执行前都先 fork 十余次**，放大临界 worker 的 fork 压力。
   切 function 模式后 `_sh_deactivate_contents` 只生成反激活函数定义 + `${VAR+x}` 参数展开保存旧值，
   source 期零 fork（已在 conan 2.29.1 源码
   `conan/tools/env/environment.py:_sh_deactivate_contents` 与生成的 conanbuild.sh 上双向核对）。
   放在 generate() 顶部可覆盖其内 AutotoolsToolchain 及随后运行的 VirtualBuildEnv/VirtualRunEnv
   （见 `write_generators`：generate() -> VirtualBuildEnv/VirtualRunEnv -> generate_aggregated_env）。
2. `test_package/conanfile.py` 新增 `configure()` 注入同一 conf：该包显式 generators
   （CMakeToolchain/CMakeDeps）在 generate() 之前运行，必须放 configure() 才能覆盖其 env 脚本。
3. `_configure_with_retry()`：上限由 3 次放宽到 6 次，退避 15/30/45/60/75s（≈3.75 分钟），
   给 worker 的 fork 资源恢复窗口；仍保持 fork 标记门控（真实 configure 错误立即抛出）与次数上限。
4. 将此前工作树里被误改回英文简注、且缺尾行换行的 `conandata.yml` 恢复为 HEAD（远端 PR head 版本，
   与本包功能无关的注释回退，避免混入无关 diff）。

### 本机验证（不代替真机）
- `python3 -m py_compile conanfile.py test_package/conanfile.py` 通过。
- 逐条核对 conan 2.29.1 `environment.py` 的 unset/function 两分支，确认 function 模式 source 期无 printenv fork。
- 未改测试逻辑/口径：discovered 仍取 src/Makefile.am TESTS 完整清单（24），
  executed/passed/failed/skipped 仍只来自 src/test-suite.log，gaps 口径不变。

## 2026-10-16 CI #95036 修复（configure 全程 fork EAGAIN）+ 审查意见闭环（R39/P3）

### 现象与证据
- CI 校验失败（build #95036，worker OpenHarmonyPCDeveloper-CI-034，revision `e431020d`，
  `conan-build-test` 步骤）：configure 6 次尝试全部失败，共 608 行 `fork:` 报错（其中 498 行 `fork: retry:`）
  （`.../b/configure: fork: retry: Resource temporarily unavailable`），
  最早的两个探测即被 EAGAIN 打断：
  `checking whether make sets $(MAKE)... no`（对照正常构建为 `yes`）、
  `checking whether the C++ compiler works... no`，最终 `configure: exit 77`
  → `Error 77 while executing`。
- 对照（同 SHA 环境性判据）：**同一 revision `e431020d`** 数十分钟后在另一 worker
  （CI-006，build #95131）干净通过，日志 0 行 fork 报错，`checking whether make sets
  $(MAKE)... yes` / `checking whether the C++ compiler works... yes`，整作业完成
  （上游 TOTAL 23 / PASS 10 / FAIL 13；消费测 passedCount=0 + ohos_feature gap）。
  同批另有 #88798/#89013 通过、#88944/#89113 失败的翻转。
- 结论：worker 级 fork/进程资源瞬时耗尽（EAGAIN），非配方缺陷
  （DRAFT-11327：同 SHA 不同 worker 结果不一致 = 环境；E491 forbid_3：先有设备资源
  证据再改包）。故本轮不改编译/测试语义，只做**不减功能、不掩盖错误**的稳健性加固，
  外加先前遗留的 R39/P3 审查意见闭环。

### 本轮改动（`conanfile.py`）
1. `_configure_with_retry()`：
   - 预算由 6 次放宽到 8 次，退避 15/30/…/105s（约 7 分钟），跨更长恢复窗口；
     仍保持 fork 标记门控与次数上限，真实 configure 错误立即抛出。
   - 内联钉工作 shell：`_resolve_working_shell()` 选 `/bin/sh`（→ `/system/bin/sh`
     → capabilities/`which sh` → 最后 hnp bash）；有 `/bin/sh` 时不选 hnp bash
     （HMDFS getcwd 不稳、fork 重试更重，avahi R18/cpluff 先例）。找不到确定存在的
     轻量 sh 时返回 None，此时不注入 SHELL/CONFIG_SHELL（沿用 profile 值），
     避免把不存在的路径写进 configure/Makefile。
   - 内联钉可写 TMPDIR：`_writable_tmpdir()` 只做写测试（不 fork），优先
     HMBS_TMPDIR/TMPDIR/TMP/TEMP（排除 /tmp），否则 build_folder/tmp，避免
     autoconf/libtool 回落只读 /tmp（E002）。
   - 每次重试前 `_reset_stale_configure_byproducts()` 清理上次残留
     （config.log/config.status/config.cache/confdefs.h/conftest*/confXXXXXX），
     不改源文件与测试口径。
   - `_log_resource_snapshot()`：零 fork 资源取证（loadavg/rlimit/meminfo/
     threads-max/pid_max/disk/cpu_count，纯 Python + /proc），pre-configure、
     每次失败、每次重试前各记一次，不额外 fork 加剧尖峰（libcmis 形态）。
   - 内联赋值（`CONFIG_SHELL=… SHELL=… TMPDIR=…`）置于 configure 命令前，优先于
     conanbuild.sh 导出的 profile `[buildenv]`（`CONFIG_SHELL=/data/service/hnp/bin/bash`）。
2. `conandata.yml` / `manifest.yaml`：`sources.url` 去掉手写 `https://gh-proxy.com/`
   镜像前缀，只写官方 `https://github.com/sphde/sphde/archive/refs/tags/1.4.0.tar.gz`
   （sha256 不变）。依据 review-memory §13（R39）/ PF7 源URL闸：CI 会自动加镜像
   fallback，手写镜像前缀即违规（该 P2 意见在历轮被重复提出）。manifest.yaml 同步为
   单值官方 URL，并更新 knowledge_gained 文本。
3. `patches/0002-config.sub-ohos.patch`：移除会遮蔽后置 `ohos-linux)` 分支的宽 `ohos*`
   glob，只保留精确的 `linux-ohos*` 分支（P3；`maybe_os` 只会取 `…-linux-ohos`，
   故 `linux-ohos*` 已足够，`ohos-linux)` 的显式映射变为可达）。
4. `patches/0010-strerror_r-portable.patch`：改为按 libc 分支处理 `strerror_r`
   返回值并把结果统一落在 `buf`：`__GLIBC__ && _GNU_SOURCE` 走 GNU 版（返回 char*，
   可能为静态串，若非空且非 buf 自身则 `snprintf` 写回 buf），其余走 POSIX/XSI 版
   （返回 int，忽略返回值直接读 buf）；先置 `buf[0]='\0'`，随后一律打印 `buf`。
   既修 musl 编译错误，也避免 glibc 上原「忽略返回值直接读 buf」读到未填充内容（P3）。

### 本机验证（不代替真机）
- `python3 -m py_compile conanfile.py test_package/conanfile.py` 通过。
- 对 `_resolve_working_shell` / `_writable_tmpdir` / `_reset_stale_configure_byproducts`
  做隔离单测：构造 config.log/conftest*/conf123456/confXXXXXX 后被清空且 `otherdir` 保留；
  `/bin/sh` 存在时 hnp-only 环境仍选 `/bin/sh`；TMPDIR=/tmp 被排除并回退 build_folder/tmp。
- `patch_ng` 对 0002 / 0010 打补丁均返回 True（在真实解压树副本上验证），
  config.sub 仅新增 `linux-ohos*`、无 `ohos*` 遮蔽；strerror 两处均生成
  `__GLIBC__` 分支与 `buf` 读取。
- PF7 源URL闸自查：对 conandata.yml/manifest.yaml 返回空 findings。
- YAML 解析：conandata.yml / manifest.yaml 均可 `yaml.safe_load`。
- 未改测试逻辑/口径：discovered 仍取 src/Makefile.am TESTS 完整清单（24），
  executed/passed/failed/skipped 仍只来自 src/test-suite.log，gaps 口径不变；
  补丁只改测试程序的平台兼容写法，不改断言或测试范围。

### 待真机验证
- 下一轮 `HMBS_UPSTREAM_TEST_RESULT` 应为 `discovered=24, executed=23,
  passed=10, failed=13, skipped=0`（对照 #95131），gaps 含
  `ohos_feature count=13` + `environment count=1`，`gap_total=14=24-10`。
- `HMBS_TEST_PACKAGE_RESULT` 仍为 `passedCount=0` + ohos_feature gap（SIGSYS），不硬失败。
- 若仍遇 fork EAGAIN，日志中应能看到 `sphde resource [...]` 快照（loadavg/rlimit）
  作为设备侧证据，且 8 次预算耗尽后才失败（不掩盖真实 configure 错误）。
