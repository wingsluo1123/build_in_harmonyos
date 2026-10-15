# xaric 0.13.9 适配笔记

## 编译环境
- 构建系统: autotools（autoconf 2.69 / automake 1.16 生成的发布 tar 包）
- 编译日期: 2026-10-14（本机 OHOS 交叉 conan create + W3 本地 CI 模拟全绿）
- 编译器: clang/clang++（本机为 OHOS SDK clang 15，profile `ohos-local`；CI worker 为设备自带 clang 15）
- 状态: built（交叉构建通过、W3 通过、未上传制品仓）。OHOS worker 的真机构建与 PTY
  运行由远程 CI 完成，是 rule12 的权威证据。

## 编译步骤

```bash
# 本机（macOS + OHOS SDK clang 15 交叉）实际执行：
conan create archives/x/xaric/0.13.9 -pr:h=ohos-local -pr:b=ohos-local --build=missing
CONAN_PROFILE=ohos-local python3 scripts/ohc-run.py finish xaric 0.13.9 built   # W3 阻塞门禁
python3 scripts/ohc-run.py conan-verify xaric 0.13.9 --profile ohos-local        # G0-G4 报告

# 配方内部等价于：
#   configure --prefix=<pkg> --with-openssl=<openssl.package_folder>
#     --host=aarch64-unknown-linux-ohos --build=<真机同值 / 本机 x86_64-apple-darwin>
#   CFLAGS 注入 -I<ncurses>/include 与 -fcommon；LDFLAGS 注入 -L<ncurses>/lib
#   make -j1 && make check -j1（Automake 空目标，随后打印 HMBS_UPSTREAM_TEST_RESULT）

# 早期 macOS 原生辅助验证（仅作旁证，rule12 以 OHOS worker 为准）
tar xzf xaric-0.13.9.tar.gz && mkdir build && cd build
../xaric-0.13.9/configure --prefix=$TMPDIR/xaric-install
make -j4 CFLAGS="-O2 -DSYS_SIGLIST_DECLARED"   # macOS 已声明 sys_siglist 但探测失败，需绕过
script -q /dev/null ./xaric -v                 # → Xaric 0.13.9（main() 需要 PTY）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `i can not find tgetent` | OHOS 无 libtermcap/libcurses；Conan ncurses 仅提供 libncursesw.a，而 xaric 的 tgetent 搜索链（termcap/termlib/curses/xtermcap）不试 -lncursesw | 补丁 0001-tgetent-ncursesw.patch：在 -lcurses 与 -lxtermcap 之间插入 -lncursesw 探测（configure.ac 与生成的 configure 同步修改）。**坑**：AC_CHECK_LIB 是嵌套 if/else 链，链上库数 4→5，configure.ac 末尾闭合括号与生成 configure 的 `as_fn_error` 之后闭合 fi 都要多一个；漏 fi 时 macOS bash 3.2 的 `sh -n` 可能通过但执行到 config.status 阶段 exit 258，必须 `bash -n` 与 `sh -n` 双验证 |
| 2 | configure 报 `failed to find OpenSSL`（若未注入） | AX_CHECK_OPENSSL 硬依赖：找不到 openssl/ssl.h 或链接失败即 AC_MSG_ERROR | `--with-openssl=<openssl.package_folder>` 绕过 pkg-config，直接指向 Conan openssl 包（include/openssl/ssl.h + 静态 libssl.a/libcrypto.a） |
| 3 | `./xaric -v` 报 `Woops I need a tty!` | main() 先 `isatty(0)` 检查（irc.c:798），非 TTY 直接 exit(1) | test_package 用 python3 pty 模块驱动二进制，捕获 PTY 输出断言 "Xaric 0.13.9" |
| 4 | macOS 本地 sys_siglist 重定义 | macOS SDK 已声明 sys_siglist，但 xaric configure 的探测程序未通过（macOS 特有），走 sig.inc 生成路径 | 本地原生验证仅用 -DSYS_SIGLIST_DECLARED 绕过；OHOS 交叉/真机走 sig.inc 生成或原生探测，无此冲突（非适配点，不修改上游） |
| 5 | 本机交叉构建 `configure: error: cannot run C compiled programs`（真机原生不复现） | 该 configure 无 AC_CANONICAL_HOST，tar 包也不带 config.sub/config.guess（build-aux 只有 compile/depcomp/install-sh/missing），AutotoolsToolchain 因此不注入三元组，configure 停在 native 模式去执行刚链接出的 a.out | 配方显式追加 `--host=aarch64-unknown-linux-ohos`；真机 `--build` 取同值（保持原生探测），本机取 `x86_64-apple-darwin` 进 cross 模式；交叉分支钉 `ac_cv_ipv4=yes ac_cv_ipv6=yes`，使本机构建编译与真机相同的源码路径（iflist.c/ga_nsearch.c）。E205 的 patch-script 处方针对“带 config.sub 但不认 ohos 三元组”的项目，本包无该文件可补故不适用；仓内先例 slrn/1.0.3、scws/1.2.3 同法 |
| 6 | cross 模式 `configure: error: cannot run test program while cross compiling`（SA_CHECK_SOCKOPT） | sa.ac 的 `AC_RUN_IFELSE` 第 4 参数（action-if-cross）为空，autoconf 2.69 生成 `as_fn_error` 硬失败 | 补丁 0002-sockopt-cross-fallback.patch 为 SO_RCVTIMEO/SO_SNDTIMEO 补 cross 分支，取真机原生探测的答案 yes（musl 声明且内核实现）。真机走原生分支，补丁在 CI 上惰性 |
| 7 | `make: *** [aclocal.m4] Error 127`、`aclocal-1.16: command not found` | 0001/0002 改了 sa.ac 与 configure.ac，二者正是 `am__aclocal_m4_deps`，mtime 晚于 aclocal.m4 → automake maintainer 规则要求重生成，而构建机无 aclocal/automake | build() 在 apply_conandata_patches 之后按依赖序 `os.utime` 重打 aclocal.m4 → configure → config.h.in → Makefile.in（命中 E248 的 fix-mtime-after-patch，本包扩展到整条生成链） |
| 8 | `ld.lld: error: duplicate symbol: term_scroll / term_insert / term_delete / term_cursor_left` | ircterm.h 把 4 个函数指针写成暂定定义，ircterm.c 又重复定义其中 2 个；clang ≥ 10 默认 `-fno-common`，每个包含该头的 TU 都发出强符号 | CFLAGS 追加 `-fcommon` 恢复合并语义（同类 DRAFT-fermi-lite-0.1-header-tentative-definition-duplicate-symbol；仓内先例 rotter/0.9、wily/0.13.42、wise/2.4.1） |
| 9 | `ld.lld: error: duplicate symbol: trace`（另一侧为 libncursesw.a 的 lib_trace.o） | ncurses 也导出 `trace`；Conan 的 ncurses 是**静态** libncursesw.a，该成员被整体拉入链接。动态系统 ncurses（如 macOS libncurses.dylib）时可执行文件定义优先，故原生验证不暴露 | 补丁 0003-trace-symbol-collision-ncursesw.patch 把 xaric 自己的调试函数 `trace()` 改名 `xaric_trace()`（irc.c 定义 + irc.h 声明 + TRACE() 宏）。两者语义不同（varargs 日志 vs `char *trace(unsigned)`），**不能**用 DRAFT-14410 首选的 `-Wl,--allow-multiple-definition`，改用其 fallback 2「改名」 |
| 10 | 本机 W3 的 L1e 破坏性反向测试会判 test_package 为空壳 | test() 在 `can_run(self)` 为假时直接 return，CI 把 bin/ 移走后 `conan test` 仍退出 0 | test() 先做产物断言（bin/xaric 存在且可执行、ELF magic、`e_machine == 0xB7` AArch64、help/help 存在）再按 can_run 决定是否跑 PTY 脚本；L1e 实测 `[ok] Negative test confirmed` |

## 源码修改

- `patches/0001-tgetent-ncursesw.patch`
  - configure.ac: tgetent 搜索链插入 `AC_CHECK_LIB(ncursesw, tgetent, LIBS="-lncursesw $olibs", ...)`
  - configure（tarball 内生成脚本）: 对应插入 -lncursesw 探测块（与 configure.ac 同步）
  - 补丁类型: portability（OHOS 无 libtermcap/libcurses 的系统差异）
- `patches/0002-sockopt-cross-fallback.patch`
  - sa.ac: `SA_CHECK_SOCKOPT` 的 `AC_RUN_IFELSE` 补 action-if-cross（原来为空 → 硬失败）
  - configure: SO_RCVTIMEO / SO_SNDTIMEO 两处 `if test "$cross_compiling" = yes` 分支由
    `as_fn_error "cannot run test program while cross compiling"` 改为按 yes 处理并写
    `#define USE_SO_*TIMEO 1`（与 sa.ac 同步）
  - 补丁类型: portability（交叉构建可运行性；真机原生分支不受影响）
- `patches/0003-trace-symbol-collision-ncursesw.patch`
  - irc.c / irc.h: 自有调试函数 `trace()` → `xaric_trace()`（含 TRACE() 宏调用点）
  - 补丁类型: portability（静态 libncursesw.a 符号冲突；仅改名，无行为变化）
- 补丁均由真实修改树 `diff -u` 生成（a/ b/ 前缀，与 0001 同格式），逐个 `patch -p1 --dry-run`
  验证可应用，并对生成的 configure 做 `sh -n` + `bash -n` 双语法校验。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| openssl | 3.5.6.1 | AX_CHECK_OPENSSL 硬依赖；静态库（no-shared），产物 DT_NEEDED 不含 libssl/libcrypto |
| ncurses | 6.6 | 提供 termcap.h/curses.h + libncursesw.a（含 tgetent，tinfo 已并入） |

## 验证结果

```text
# 测试清点（R51 三步法；口径：上游构建系统注册的自动化用例数）
#   构建入口: Makefile.am 只有 bin_PROGRAMS/man_MANS/EXTRA_xaric_SOURCES，无 TESTS/
#             check_PROGRAMS/check_SCRIPTS/check-local → make check 是 Automake 空目标（0 用例）
#   全包扫描: tar 包 143 条目，仅 build-aux/ 与 help/ 两个子目录，无 test/tests/check/
#             spec/regression/corpus/fixture 目录
#   内容扫描: configure.ac 未配置任何测试框架；ga_echeck.c 是 getaddrinfo 辅助实现（非测试）
#   build() 内真跑 `make check -j1` 退出 0，并打印机器标记（w3-local-ci.log:676）：
#     HMBS_UPSTREAM_TEST_RESULT={"status": "no_tests", ..., "discovered": 0, "executed": 0,
#                                "passed": 0, "failed": 0, "skipped": 0}
#   → 上游用例数 0，通过率 0/0（无用例可跑）

# 鸿蒙特有测试（rule12）: N = 1 个用例 = test_xaric.sh 的 3 项断言
#   口径：独立断言项（bin 可执行 / help 数据已安装 / PTY 输出含 "Xaric 0.13.9"）
#   复核：grep -n '|| fail' test_package/test_xaric.sh → 6 处 = 3 个参数与环境守卫 + 3 项断言
#   交叉构建下的产物断言（ELF/e_machine/help）是打包完整性检查，不计入 rule12 断言数

# 本机 W3（CONAN_PROFILE=ohos-local；reports/w3-local-ci.log）
L0_RESULT=pass: all checks passed        # 含 L0i 依赖在仓 / L0j 版本冲突 / L0k commands.json / L0m 结构
L1_RESULT=pass: upstream tests + test_package executed
[ok] L1c: Upstream official tests (make check/ctest) executed in build phase
[ok] L1e: Negative test confirmed — test genuinely depends on xaric
L2_RESULT=skip: xaric version/help failed   # OHOS aarch64 ELF 无法在 macOS 构建机执行（非阻塞）
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
KC_ERRORS=0 / JC_ERRORS=0 / Pass rate: 100.0% (1/1) / All packages built and tested successfully
.ci-result.json: exit_code=0, step=W3_local_ci, timestamp=2026-10-14T14:53:50,
                 integrity_hash=6e2d71a61a338860,
                 log_sha256=ba7da05ead80d1094cd53560443962931f6863adb276475f3af17ed585fc4d23

# 产物
bin/xaric: ELF 64-bit LSB pie executable, ARM aarch64, interpreter /lib/ld-musl-aarch64.so.1
llvm-readelf -d → NEEDED 仅 libc.so（openssl、ncursesw 静态链接；R26 无系统同名 .so 产出）
package ref: xaric/0.13.9#834b59b7c0a100d78c5b104750afaf10:677c45dcaf48fe87adb4d3888c42da4b7f1eb7ee#ac21c5953916ad9f275ccf1293fc16c6
share/xaric/help/{help,copying,warranty}、share/man/man1/xaric.1
packaging/xaric-0.13.9-ohos-aarch64.tar.gz sha256=f67d53241e18d8cd9d7a32312e8391435ad8755cc797b6416bd2412496e90fc6

# test_package 输出（本机交叉）
packaged xaric: AArch64 ELF present, help data installed
Cross build: packaged xaric verified as an AArch64 ELF; the PTY run in test_xaric.sh executes on the device

# test_package（OHOS worker，rule12 权威证据；CI 后回填）
#   sh test_xaric.sh <pkg>/bin <pkg>/share/xaric
#   → 期望 PASS: installed xaric starts under PTY and reports version 0.13.9
```

## 注意事项

- 上游无正式测试框架；`make check` 已在 build() 内真跑并输出 no_tests 机器标记，适配后新增
  1 个鸿蒙特有测试（3 项断言）。
- 本机交叉与真机原生的已知差异（均记录在 reports/test-report.md，非缺陷）：
  1. SA_CHECK_SOCKOPT 在 cross 分支按 yes 处理（0002），真机跑原生探测；
  2. sys_siglist 探测在 cross 下不执行，本机由构建机头文件生成 sig.inc，真机自行探测/生成，
     仅信号名表内容可能不同，不影响编译链接；
  3. 本机无 binary-sign-tool，签名步骤跳过（日志 `OHOS signing tools unavailable`），CI worker 会签名；
  4. L2 冒烟在本机 skip（无法执行 OHOS ELF），CI 真机可执行。
- finish 的 Step 4 conan-verify 默认使用仓库 profile `ci/conan/profiles/ohos-aarch64`
  （编译器指向设备路径 `/data/service/hnp/bin/clang`），在 macOS 上必然失败并把 status 翻成
  failed。本机口径改用 `conan-verify xaric 0.13.9 --profile ohos-local` 取得真实 PASS 报告
  （reports/conan-verify-report.md），status 依 R29 记为 built（验证通过、未上传）。
- xaric 是终端程序，运行时必须提供 TTY；测试与使用方式与普通 CLI 不同。

## 知识沉淀

### 本次新增草稿（知识库扩展增量，1 对）

- 草稿：`knowledge/drafts/DRAFT-xaric-0.13.9-autotools-tgetent-chain-ncursesw.kv`（+ 同名 `.md`）。
- 解决的一类问题：**经典 Autotools 嵌套 AC_CHECK_LIB 库搜索链（termcap/termlib/curses/xtermcap）不识别 -lncursesw**，而 OHOS ncurses/6.6 只交付 libncursesw.a（termcap/tinfo 符号已并入），导致 configure 检测 tgetent 硬失败。同类面为 ircII 家族等 1990–2000 年代 TUI/终端工具。
- 与既有条目的区别：`cdcd-0.6.6-legacy-autotools-ohos-detection-mismatches` 覆盖的是**单层** `AC_CHECK_LIB(curses, tputs)` 改名 ncursesw；本条增量是**嵌套链插入**修复模式（configure.ac 嵌套括号计数、生成 configure 的 fi 闭合 4→5、bash 3.2 `sh -n` 漏报、`ac_cv_lib_*` 强分支验证）。
- 撞库（engine + index.tsv + doc/drafts 全文检索）结论：核心机制同族但嵌套链插入式修复未覆盖，故新建草稿，kv 已填 similar_to。

### 本次命中并复用的既有知识（路径 A 部分，未新增条目）

| 现象 | 命中条目 | 采用处方 |
|------|----------|----------|
| 补丁后 make 调 aclocal-1.16 报 Error 127 | `knowledge/graph/E248.kv` | fix-mtime-after-patch（os.utime 按依赖序重打） |
| 静态 libncursesw.a 与程序同名符号冲突 | `knowledge/drafts/DRAFT-14410-static-ncurses-beep-duplicate-symbol.kv` | 语义不同 → 用其 fallback 2 改名，而非 --allow-multiple-definition |
| 头文件暂定定义导致 duplicate symbol | `knowledge/drafts/DRAFT-fermi-lite-0.1-header-tentative-definition-duplicate-symbol.kv` | -fcommon |
| 交叉构建三元组/平台识别 | `knowledge/graph/E205.kv` | 其 patch-script 处方不适用（本包无 config.sub/config.guess）；改按仓内先例 slrn/1.0.3、scws/1.2.3 显式传 --host/--build |
## 远程 HarmonyOS CI 终态（2026-10-14）

- PR：**#15751**（https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/15751，head `songzhenyan:feat/xaric-0.13.9` → main）
- 构建：**#91339 构建成功**，worker `OpenHarmonyPCDeveloper-CI-005`，SHA `269c04ca`，7/7 个构建步骤全绿
- 门禁：Conan test_package ✅（真机执行，rule12 的 PTY 断言在设备上通过）、L0 ✅、L1 ✅（L1e ✅ 破坏性反向测试）、L2 ✅、L4 ✅、L5 ✅、包产物 1 ✅
- 制品：CI 已 `uploaded xaric/0.13.9` → 依 R29（conan_verify PASS + CI upload）状态由 built 升为 **published**
- AI 检视（atomgit-bot）：`✅ 未发现问题`，0 条意见，无未闭环 review thread（rule6/rule11 满足）
- 与本机差异的收敛：本机 skip 的 L2 冒烟在真机为 ✅；本机交叉分支假定的 SO_RCVTIMEO/SO_SNDTIMEO 与 sys_siglist 由真机原生探测决定，构建与测试全绿说明假定与真机一致
- 触发方式：`gitcode_pr.py trigger-ci`（/rebuild，note_id 193757083）；`submit` 的 create-pr 以裸分支名调用会报 `Can not find the branch`，跨 fork 需 `owner:branch` 写法，故本 PR 由 `gitcode_pr.py create-pr --source songzhenyan:feat/xaric-0.13.9` 直建

## 远程 CI 三轮定位与 HMDFS 加固（2026-10-14 晚）

| 构建 | worker | 失败点 | 真因 | 处置 |
|------|--------|--------|------|------|
| #91339 | CI-005 | — | 全绿：7/7 步骤、test_package ✅、L0/L1(L1e)/L2/L4/L5 ✅ | SHA 269c04ca 的配方已获真机验证 |
| #91468 | CI-028 | `checkout-pr` | worker 拉 PR diff 被限流：`curl: (22) ... error: 429`（CI 自带脚本，非本仓代码） | /rebuild 重试 |
| #91585 | — | `configure` 末尾 | **HMDFS 确定性故障**：config.status 以 `(umask 077 && mktemp -d ./confXXXXXX)` 建临时目录，HMDFS 强制 setgid 并重映射 owner UID，目录变成 `drwx--S---`，连属主都写不进去 → `./config.status: line 615: ./confCFcHBK/subs1.awk: Permission denied` → `config.status: error: could not setup config files machinery`。第 615 行即 `echo 'BEGIN {' >"$ac_tmp/subs1.awk"`（本机生成的 config.status 同行号核对） | 新增补丁 0004（去掉两处 `umask 077`），与 qsopt/2.5.10.3、roll/2.7.0、a52dec/0.7.4 同款，命中 E011/E114 |
| #91592 | — | `configure`/`make` | **worker 进程资源耗尽**：满屏 `configure: fork: retry: Resource temporarily unavailable`，导致 `checking whether the C compiler works... no` → `C compiler cannot create executables`、`checking whether make sets $(MAKE)... no`、`make: *** [Makefile:442: xaric-irc.o] Error 1`。同一时段 puzzles PR 也出现 `cannot fork() for git-remote-https`，属 fleet 级抖动 | 只能重跑，非配方可修 |

- 结论：配方本身在真机已验证（#91339）；#91468/#91592 为 worker 侧限流与 fork 耗尽，#91585 为可由配方消除的 HMDFS 权限形态。补 0004 后，config.status 不再依赖 0700 临时目录，HMDFS worker 与 release 流水线都不会再撞这一类失败。
- 0004 由真实修改树 `diff -u` 生成（仅动 configure 的两行），`patch -p1 --dry-run` 可应用，`sh -n` + `bash -n` 双语法校验通过；本机 ohos-local 交叉 `conan create` 复验通过（该改动在本机惰性）。
- **状态纠正**：CI 评论里的 `uploaded xaric/0.13.9` 是「包产物」行，PR 流水线执行的是 `build_and_test.sh`（**不带** `--upload`），只有 release 流水线才上传。用 Conan v2 REST 直查制品仓：
  `GET .../v2/conans/xaric/0.13.9/_/_/revisions` → **404 error:not found**（对照 `openssl/3.5.6.1` → 200 带 revision）。
  故依 R29 把 `manifest.yaml` 的 `status` 从 published 纠回 **built**（验证通过、未上传）；`conan list` 按 R35 不作为存在性判据。
- 版本不变（R37）：制品仓无 0.13.9，L0j 的「已发布且配方不同」不会触发，无需加修复后缀。
---

**编译结束**: 2026-10-14 19:20
**最终状态**: built
