# ifmail 2.14tx8.10 — 适配笔记

任务：【知识库扩展】｜语言 c（C，非 C++；任务表里的 "C++" 与源码不符，实测 133 个 .c / 61 个 .h / 0 个 .cpp）｜构建系统 makefile（顶层 Makefile + `include CONFIG`，无 configure/cmake/meson）｜首次适配
上游：<http://ifmail.sourceforge.net/>（原 www.average.org/ifmail 已改为 2001 年的跳转页）
源码：`ifmail_2.14tx8.10.orig.tar.gz` 501678 B，sha256 `5135f3bb0373bb82b983e7db61294fc56827538409cf56a1c5e45aee8f26d920`
分支：`feat/ifmail-2.14tx8.10`（基于 ohpcd/main `e3aaad7dbb`，2026-10-16）

> 证据纪律：本文所有"实测"均为本机可复核结果；凡未在真机验证的结论一律显式标注 **【推断】**。

---

## 0. 查重（W1/W0 之前）

| 检查项 | 命令 | 结果 |
|---|---|---|
| 本仓归档 | `find archives -iname '*ifmail*'` | 无 |
| main 内容 | `git grep -il ifmail origin/main` | 无 |
| 制品仓 | `conan list "ifmail*" -r=ohpcd` | `Found 0 pkg/version recipes` |
| 远程分支 | `git ls-remote --heads {origin,upstream,ohpcd} \| grep -i ifmail` | origin 无；upstream/ohpcd 有 `feat/ifmail-2.14tx8.10` → `b544378a4e` |

`b544378a4e` 与当时的 main HEAD 完全相同（`!14290 merge feat/samarium-1.0.0 into main`），
即该分支是平台预建的占位分支、**不含任何提交**，不构成"已被有效任务占用"。本次从
ohpcd/main `e3aaad7dbb` 重新切出同名分支。

## 1. 源码来源（R39 / PF7 例外，已预先声明）

tx8.10 的原版 tarball 只剩 Debian pool 一份，排查过程（全部实测）：

| 候选源 | 实测 | 结论 |
|---|---|---|
| www.average.org/ifmail（LSM 登记的官方站） | HTTP 200，256 B，`META Refresh → ifmail.sourceforge.net` | 已迁移 |
| SourceForge `projects/ifmail/files/ifmail-stable/` | 只有 2.9 / 2.10 / 2.11 / 2.12 / 2.13 / 2.14 / 2.15 / 2.8f / 2.8g | 无 tx 分支 |
| SourceForge `ifmail-devel/` | 只有 3.02 / 3.03 | 无 tx8.10 |
| GitHub `search/repositories?q=ifmail` | 5 个仓，全是下游 fork（larsks/ifmail-lks、pld-linux/ifmail …） | 非官方 |
| AUR `rpc/?v=5&type=search&arg=ifmail` | `resultcount: 0` | 无 |
| Debian pool `.orig.tar.gz` | 200，501678 B | **唯一存世原版** |

- sha256 双向核对：`shasum -a 256` 本机实测值 == `ifmail_2.14tx8.10-32.dsc` 的
  `Checksums-Sha256` 条目（同文件 501678 B）。
- **未使用** Debian 的 `-32.debian.tar.xz` quilt 系列（20+ 个下游补丁），本次全部
  可移植性修改都是自己写的 `patches/0001..0015`，与 Debian 补丁无继承关系。
- PF7（Debian host 黑名单）会命中此 URL，属"上游官方源已消失、只剩 Debian pool 原版"
  的例外，与 `archives/r/rdate/1.11`、`archives/r/rcs/5.10.1` 同族；submit 需
  `--no-preflight` 并以本节为理由。conandata.yml 顶部已写同样的预声明。
- CI 取源风险预声明：镜像改写只覆盖 github.com，deb.debian.org 直连。

## 2. 依赖预检（W0，R35/R36）

| 依赖 | 用途 | 制品仓实测 | 处置 |
|---|---|---|---|
| gdbm/1.23 | ndbm 兼容层（`dbm_open/dbm_store/dbm_fetch/dbm_firstkey/dbm_nextkey/dbm_delete`） | `conan download gdbm/1.23 -r=ohpcd` 后包内实测有 `include/{ndbm.h,dbm.h,gdbm.h}` + `lib/libgdbm_compat.a`（静态，`shared=False`） | `requires("gdbm/1.23")` |
| gdbm/1.24 | 同上（候选） | 配方实测 `--disable-libgdbm-compat`，包内**没有** ndbm.h/dbm.h/libgdbm_compat | **不可用**，必须选 1.23 |
| bison/3.8.2 | `iflib/parsedate.y`、`ifcico/flagexp.y` | 在册且有 OHOS 二进制 | `tool_requires`（仅 worker 原生构建） |
| flex/2.6.4.2 | `ifcico/flaglex.l` | 同上 | 同上 |
| awk/20251225 | `ifcico/mkprod.awk` 生成 `ftscprod.c` | 同上 | 同上 |
| libresolv | CONFIG 的 Linux `LIBS = -lgdbm -lresolv` | OHOS musl 把 resolver 并入 libc，**无 libresolv** | 从 LIBS 去掉，改本地实现（补丁 0002） |
| libintl/gettext | `USE_NLS=yes` 时 po/ 需要 msgfmt + libintl | 有 gettext 包，但 NLS 只影响交互消息本地化 | `USE_NLS=no`（非核心可选功能，见 §7） |

`tool_requires` 按仓内既有约定（libidl2/0.8.14、seexpr/3.0.1、scws/1.2.3）用
`user.build:flex_bison_native` 分流：worker 原生构建走 tool_requires，macOS 开发机用
OHOS settings 模拟时走宿主 bison/flex/awk。

## 3. 构建系统分析

- 顶层 `Makefile` 只有一句 `include CONFIG` + `DIRS = iflib ifgate ifcico`（`USE_NLS=yes`
  时追加 po/），`all` 逐个 `cd $d && ${MAKE} all`。
- `CONFIG`（530 行）是纯 make 变量文件：路径常量、`OPTS`（通用 + Linux/x86 平台块）、
  `CC/CFLAGS/LDFLAGS/LIBS/YACC/LEX/AWK/AR/RANLIB/INSTALL/SHELL`、`NEEDED`（缺失函数补齐）、
  `OWNER/GROUP/MODE/SMODE`（install 时 chown/setuid）。
- **没有 configure**，因此平台选择只能走 make 命令行覆盖（命令行变量优先级高于
  CONFIG 里的 `=` 赋值；`OPTS +=` 的平台块保留不动，只通过 CFLAGS 追加 `-DDO_NEED_TIME`）。
- CONFIG 自带的 Linux OPTS 块对 musl 基本适用（实测 `sys/vfs.h`、`regex.h`、`termios.h`、
  `struct sigcontext` 都在），只有 `DO_NEED_TIME` 缺失（见补丁说明）。
- `make install` 用 `${INSTALL} -s -o fnet -g fnet -m 4710`（strip + chown + setuid），
  非 root 且交叉场景都不可用 ⇒ **不调用 install**，`package()` 直接 copy 产物；
  setuid 位不带入包（ifcico 的串口/锁文件特权路径在 OHOS 上无意义）。
- 生成物：`iflib/parsedate.c`（bison）、`ifcico/flagexp.c`+`flaglex.c`（bison/flex）、
  `ifcico/ftscprod.c`（awk）、`ifcico/version.c`+`ifgate/version.c`（`./lastmtime` 现场编译运行）。

## 4. 适配点逐条（15 个补丁）

按"构建参数 → 上游已有抽象 → 最小源码补丁"的顺序，全部落在源码/构建脚本层，
**没有任何 `__OHOS__` 平台宏**（R8/PF5）。

| # | 文件 | 根因（实测报错） | 修法 |
|---|---|---|---|
| 0001 | ifcico/hydra.c | `error: incompatible integer to pointer conversion assigning to 'char *' from 'int'`（`xtodos` 无原型，隐式 int） | 补 `extern char *xtodos(char*);`（定义在 filelist.c） |
| 0002 | ifcico/mxlookup.c | `error: use of undeclared identifier '_res'`；链接期 `undefined symbol: _getshort/_getlong` | musl 只有 `struct __res_state` 类型（头文件自注 "unused; purely for broken apps"）没有 `_res` 对象，也无 libresolv 私有符号 ⇒ 删两行 resolver 调参，`_getshort/_getlong` 换本地大端读取 |
| 0003 | ifcico/respfreq.c | `varargs.h:11:4: error: "Please use <stdarg.h> instead"`；链接期 `undefined symbol: re_comp/re_exec`（ld.lld 提示 did you mean: regcomp） | `add_report()` 转 C99 stdarg（含前置声明改 `static void add_report(char*,...)`，否则 `conflicting types`）；BSD `re_comp/re_exec` 用 POSIX `regcomp/regexec` 包一层，保持两处调用点原样 |
| 0004 | ifgate/message.c | `ld.lld: error: duplicate symbol: ref_dbase`（ifmail.o 与 message.o 各一份暂定定义） | 改 `extern`（与同目录 mkrfcmsg.c 已有写法一致），定义归 ifmail.c |
| 0005 | ifgate/nlindex.c | `ndbm.h:42:3: error: typedef redefinition with different types ('struct DBM' vs 'struct DBM')` + clang 提示 "unguarded header" | 删掉重复的 `#include <ndbm.h>/<dbm.h>`，由 nlindex.h 单点包含 |
| 0006 | ifgate/nodecheck.c | 同上 | 同上，但保留原本嵌在 `#ifdef HAS_NDBM_H` 里的 `<fcntl.h>`（O_RDWR/O_CREAT 需要） |
| 0007 | iflib/testglue.c（新增） | `make testconf` 链接期 `Undefined symbols: _usage, _version`（还有 reldate/copyright） | 上游 `rdconfig.o` 引用前端程序提供的 4 个符号而 iflib 自己一个都没有 ⇒ 补测试专用 glue（不进任何出厂二进制） |
| 0008 | iflib/lutil.c | `varargs.h` #error 桩；`va_dcl` → `error: expected function body after function declarator`；`va_start(args)` → `too few arguments provided to function-like macro`；`xstrcpy/xstrcat` 隐式 int | `loginf/logerr/debug` 三个入口转 `<stdarg.h>`（lutil.h 本来就是 ANSI 声明 `void debug(unsigned long,char*,...)`，定义侧一直是 K&R，两侧本来就不一致）；补 `#include "xutil.h"` |
| 0009 | iflib/make_new_ref.c | `warning: call to undeclared library function 'exit'` | 补 `<stdlib.h>` |
| 0010 | iflib/trap.c | `bits/alltypes.h:357: error: typedef redefinition ('struct __sigset_t' vs 'struct sigset_t')`、`bits/signal.h:93: redefinition of 'sigaltstack'`、`signal.h:93: redefinition of 'sigval'` | OHOS clang 定义 `linux` 且不定义 `__GLIBC__`，于是走进 pre-glibc 分支 `#define __KERNEL__` + `<linux/signal.h>`，内核头与 musl 用户态头撞车 ⇒ 删掉该分支（glibc 本来也不会走），musl 自己在 `<signal.h>` 提供 `struct sigcontext`（实测 sysroot `bits/signal.h:18`）；顺带补 `<stdlib.h>`（abort 隐式声明） |
| 0011 | ifcico/flaglex.l | `lex.yy.c:642:21: error: too many arguments provided to function-like macro invocation`（flex 生成 `extern int yywrap ( void );`，文件里 `#define yywrap() 1`） | 按 flex 约定 `#define YY_SKIP_YYWRAP 1`，调用点仍用宏 |
| 0012 | ifgate/nlindex.h | `nlindex.h:37:25: error: array has incomplete element type 'struct _fkey'` | `struct _fkey` 只在 ifcico/nodelist.h 定义，ifgate 全目录无 fkey 引用 ⇒ 删该 extern；同时补齐 ifcico 版已有的 `<dbm.h>` 回退分支 |
| 0013 | iflib/parsedate.y | `error: static declaration of 'date_lex' follows non-static declaration`（bison 生成的 yyparse 先调用后定义）；`error: incomplete definition of type 'struct tm'`；strcmp 隐式声明 | `date_lex` 去 static 并给出 `int date_lex(void);` 原型（对 bison 2.x 的隐式声明与 3.x 可能自带的原型都成立）；补 `<string.h>`；`struct tm` 由 `-DDO_NEED_TIME` 解决（见下） |
| 0014 | iflib/xutil.h | `#ifndef size_t / #define size_t unsigned int`（K&R 兜底宏） | 换 `#include <stddef.h>`：该宏在 LP64 上把 `xmalloc(size_t)` 变成 `unsigned int` 形参（尺寸截断），且会污染其后包含的任何系统头（`typedef unsigned long unsigned int`） |
| 0015 | iflib/Makefile | 4 个 `-DTESTING` 规则硬编码 `cc -g -Wall`，丢掉 `${CFLAGS}/${INCLUDES}/${DEFINES}/${LIBS}` | 改走与目标文件相同的变量，并把 `testglue.c` 链进 testconf/testscan |
| 0016 | ifgate/Makefile | **真机 CI 实测**：`ln: cannot create hard link from 'ifmail' to 'ifnews': Operation not permitted` → `make[1]: *** [Makefile:92: ifnews] Error 1` → 整个 `make all` 失败 | HMDFS 不支持硬链接（**命中既有知识 E079**，按其推荐方案处置）：两处 `ln`（构建规则 + install 规则）改 `cp`。`ifnews` 与 `ifmail` 是同一程序的不同 argv[0]（`setmyname()` 决定横幅与 news 模式默认值），复制等价，且 `package()` 本来就是按两个独立文件打包 |

补丁 0001-0015 由本地交叉构建的错误日志逐条定位；**0016 是唯一一条只能由真机暴露的**（macOS/APFS 支持硬链接，交叉构建与本机参考构建都不会触发），属 E079 家族。

配方侧（conanfile.py，非补丁）的两个平台决策：

- `-DDO_NEED_TIME`：`parsedate.y` 与 `gettime.c` 都写成 `#if defined(DO_NEED_TIME) #include <time.h> #endif`，
  CONFIG 只给 SCO/ISC/AIX 定义了它，Linux 块没有 ⇒ musl 下 `struct tm` 不完整
  （`error: incomplete definition of type 'struct tm'` × 16）。用上游既有开关解决，不改源码。
- `LIBS`：`-lgdbm -lresolv` → `-L<gdbm>/lib -lgdbm_compat -lgdbm`（顺序重要，compat 在前）。

## 5. 上游测试清点与执行（R51 三步法）

**第一步 清点**（源码树逐目录 grep，证据在 test_package/MANIFEST.yml）：

- `iflib/Makefile` 有 4 个 `-DTESTING` 自测目标 + 配套运行目标：
  `testconf/tryconf`（rdconfig.c）、`testscan/tryscan`（scanout.c）、
  `testtrap/trytrap`（trap.c）、`testrfcaddr/tryrfcaddr`（rfcaddr.c）。
- `ifgate/Makefile` 的 `tryt/tryn/trym/tryu/tryp` 与 `ifcico/Makefile` 的 `tryc/tryp`
  是手工调用真实二进制、依赖 `/var/spool/*` 现场数据的示例（`>/var/log/ifmail/ifdebug`、
  `cd /var/spool/ifmail/nl.d`），无可判定断言 ⇒ 不计入。
- `find . -iname '*test*'` 只命中 `ifgate/testmail`（示例邮件文本）、
  `ifgate/nodecheck.{c,h}`（节点检查逻辑，非测试）、`misc/contrib/tic/checker.pl`
  （contrib 脚本，不参与构建）。
- 结论：**上游无正式测试框架，可执行自测程序 4 个**。

**第二步 运行**：

- 3 个可执行（testconf/testscan/testrfcaddr），由 `uptests/run_upstream_tests.sh`
  在 `build()` 末尾真实构建并运行，共 **30 项独立检查项**，末尾打印
  `UPSTREAM TESTS: 30/30 check items passed`。
- testtrap **不执行，计 0 项**：`-DTESTING` 下 trap() 的收尾是 `printf("\n")` 而不是
  `abort()`（trap.c 末尾 `#ifdef TESTING / #else abort() / #endif`），处理器返回后同一条
  非法写重复触发，没有确定终态。参考构建实测：`rc=133`、stdout 0 字节、stderr 0 字节。
  按 harmonyos-porting §6.1 只断言可自洽推导的部分，不把它包装成通过。
- 上游自测目标原本在任何平台都链接不上（缺 version/reldate/copyright/usage），
  补丁 0007+0015 才让它们可用 ⇒ 这是对上游测试的**修改**，PR 正文按模板逐条说明。

**第三步 回填**：见 §6 与 PR 两张表；口径统一为"独立可判定检查项"。

## 6. 本地验证证据

计数口径（唯一口径，贯穿 MANIFEST.yml / 本文 / 构建日志 / PR 两张表）：**独立可判定检查项**。

| 验证 | 环境 | 结果 |
|---|---|---|
| `conan create`（配方 + 15 补丁 + test_package 布局断言） | macOS/arm64，`-pr:h=ohos-local -pr:b=ohos-local`（交叉） | **PASS**，14 个产物均为 `ELF 64-bit LSB pie executable, ARM aarch64` |
| `ohc-run.py conan-verify ifmail 2.14tx8.10 --profile ohos-local` | 同上 | **PASS**：G1/G2/G3/G4 + L2/L4/L5 全绿（`reports/conan-verify-report.md`、`reports/conan-create.log`） |
| 上游自测 30 项 | 参考构建（macOS/arm64 原生，同一批补丁；OPTS 里 `STATFS_IN_VFS_H→STATFS_IN_MOUNT_H`、`NEEDED=` 避开 macOS strcasestr 冲突） | **30/30 PASS** |
| 消费者测试 20 项 | 同参考构建 | **19/20**：唯一失败项是 `ifroute` 在 macOS 编不出来（macOS `<arpa/nameser.h>` 不提供 `HEADER`/`PACKETSZ`，需 `nameser_compat.h`）；OHOS 交叉构建 ifroute 成功 ⇒ 该差异属参考环境局限，不是配方问题 |
| 鸿蒙特有测试 12 项 | 同参考构建 | **11/12**：唯一失败项 OHOS-1b 断言 `index.pag` 非空，这是 gdbm compat 的两文件布局；macOS 的 BSD db 把数据写进 `index.db` ⇒ **本地不可验证**，脚本头已注明，只在真机成立 |
| 交叉构建下的执行类测试 | macOS | 按 `can_run()` 跳过（ohos-local profile 设 `tools.build.cross_building:can_run=False`），test_package 仍断言包内 14 个二进制 + maptabs 存在 |

`patch -p1 --dry-run` 对 15 个补丁在原始树逐个校验：全部 rc=0。

### 6.1 远程 HarmonyOS CI 取证（PR #16259，三轮，均未进入编译阶段）

| 构建 | Worker | 失败步骤 | 机器人诊断 | **实际根因（本次实证）** | 分类 |
|---|---|---|---|---|---|
| #96094 | CI-034 | `checkout-pr` | 网络问题：源码下载超时 `pull/16259.diff` | PR head 被 GitCode 解析成**官方仓的同名占位分支** `feat/ifmail-2.14tx8.10`@`b544378a`（平台预建、零提交），而我的提交当时只在 fork 上 ⇒ `pull/16259.diff` 返回 HTTP 200 但 **0 字节**，CI 的 `test -s pr.diff` 判空退出 | 非配方问题（PR 元数据） |
| #96105 | CI-033 | `checkout-pr` | 同上 | 同上（换 worker 复现，排除单机抖动） | 同上 |
| #96134 | CI-027 | `conan-build-test` 的 **G0** | 「未知」 | diff 已正常（188327 B / 39 文件，head=`3d2d9ec9`，变更包正确识别为 `archives/i/ifmail/2.14tx8.10`），但 G0 知识图谱完整性门禁失败：`G0b 36 个非标准命名 .kv`、`G0d index.tsv 行数(1035) vs .kv 文件数(999)` | **D 类：CI 门禁缺陷 + main 侧状态**，与本 PR 无关 |
| 第 4 轮（G0 放行后） | worker `conan-pr-check` | `conan create` 的 **build()** | — | 真机原生编译 **133 个 .c 全部通过**、`ifmail` 链接成功（15 个补丁在真机生效，包路径烤入 `/storage/Users/currentUser/.cache/conan2/p/b/ifmaida2e40823285e/p/...` 正确）；`ifgate/Makefile:92` 的 `ln ifmail ifnews` 报 `cannot create hard link ... Operation not permitted` | **C 类：平台限制（HMDFS 无硬链接）⇒ 命中 E079**，补丁 0016 已修 |

#96094/#96105 的处置：把 3 个提交推到官方仓的任务分支
`git push git@gitcode.com:OpenHarmonyPCDeveloper/build_in_harmonyos.git HEAD:refs/heads/feat/ifmail-2.14tx8.10`
（dry-run 先验证是 fast-forward `b544378a4e..3d2d9ec96d`），随后
`pulls/16259` 的 `head.sha` 变为 `3d2d9ec9`、`pull/16259.diff` 由 0 字节变为
188327 B / 39 个 `diff --git`（中途一次 HTTP 400 `merge request patch download
timed out` 是 GitCode 重算 diff 的瞬时态，20 s 后恢复 200）。

#96134 的 G0 根因（**已量化证实，非推断**）：`ci/conan/build_and_test.sh` 的
G0b/G0d 用 `E[0-9][0-9][0-9]`（恰好三位）识别正式条目，而知识库已跨过 E999。
按 CI 原式与修正式分别对 CI 基线 `c3e27421` 复算：

| 正则 | `knowledge/graph/` 计入的 .kv | `index.tsv` 的 `^E[0-9]` 行 | G0b 非标准名 | G0d |
|---|---|---|---|---|
| 现行 `E[0-9][0-9][0-9]` | 999 | 1035 | 36 | MISMATCH ⇒ fail |
| 修正 `E[0-9]{3,4}` | **1035** | **1035** | **0** | MATCH ⇒ pass |

36 个"非标准命名"文件就是 `E1000.kv` … `E1035.kv`（`git ls-tree` 实测）。
当前 main tip `d11b9806`（!16428 merge editor/kb-promote-batch-014）用修正正则复算
同样是 1999 vs 1999 MATCH，用现行正则则约 1000 个文件被判非标准 ⇒
**该门禁缺陷会影响当前所有 PR，不是本 PR 特有**。本 PR 只新增
`archives/i/ifmail/**` 与 `knowledge/drafts/DRAFT-ifmail-*`，未触碰
`knowledge/graph/` 与 `index.tsv`（协作者禁止项），因此无法也不应在本 PR 内修复；
`ci/` 属只读基础设施，按 W2 需单独框架 PR。

第 4 轮（G0 放行后）的完整取证（真机日志摘录）：

```
/data/service/hnp/bin/clang -L/storage/Users/currentUser/usr/local/lib version.o ifmail.o ... \
    -o ifmail -L/storage/Users/currentUser/.cache/conan2/p/gdbmaa77d3992c61d/p/lib -lgdbm_compat -lgdbm
rm -f ifnews
ln ifmail ifnews
ln: cannot create hard link from 'ifmail' to 'ifnews': Operation not permitted
make[1]: *** [Makefile:92: ifnews] Error 1
make: *** [Makefile:13: all] Error 2
ERROR: ifmail/2.14tx8.10: Error in build() method, line 247
L1_RESULT=fail: conan create failed
```

三条重要结论：

1. **15 个补丁在真机全部生效**：133 个 .c 无一编译错误（只剩 `-Wdeprecated-non-prototype`
   一类 K&R 风格警告），`ifmail` 成功链接 `libgdbm_compat`+`libgdbm`（静态），
   说明 gdbm/1.23 的 ndbm 兼容层、musl 的 resolver/regex/varargs 处置都成立。
2. **`ln` 是唯一硬失败**，且是本地/交叉构建**不可能**发现的一类（macOS APFS 支持硬链接）：
   HMDFS 的 nodev 挂载与分布式架构不支持硬链接 ⇒ 命中既有知识 **E079**
   （`cannot create hard link.*Operation not permitted`），按其推荐方案把 `ln` 换成 `cp`（补丁 0016）。
   源码里另有 `iflib/Makefile:82` 的 `ln -s libifmail.so.${SHVER} libifmail.so`，
   只在 `SHARED=yes` 分支生效（本配方不用共享库），故不改，仅记录。
3. 真机把 `DEBUGFILE`/`CONFIGFILE`/`MAPTABDIR` 等编译期常量正确烤成了 conan 包内路径
   （日志中的 `-D...="/storage/Users/currentUser/.cache/conan2/p/b/ifmai.../p/..."`），
   与配方设计一致。

按 §12.1：第 3 轮属外部门禁（已停止重跑），第 4 轮属 C 类平台限制并已用补丁 0016 修复 ⇒
重新触发一轮 CI 验证 0016，这是**新假设的首次验证**，不属于同因连刷。

### 6.2 远程 CI 终态（回填）

远程 HarmonyOS CI **通过（两个独立 worker 复现）**：构建 **#97651**（worker `OpenHarmonyPCDeveloper-CI-036`，20:58:39）与 **#97680**（worker `OpenHarmonyPCDeveloper-CI-011`，21:28:20），两轮均对应含补丁 0016 的构建输入（head `4e8e7ba5`；其后 `5321ee75` 只改 notes.md 与 manifest.yaml 两个文档，未触碰任何构建输入）。两轮的平台判定完全一致：7 步全 ✅（worker_preparation / worker-prep / git-clone / checkout-pr / conan-setup / **conan-build-test** / cleanup）、`Conan test_package: 通过`、`L0 门禁 (结构完整性): 通过`、`L1 门禁 (测试执行验证): 通过`。

完整时间线（由 PR 评论的 `CI-BOT` 标记与 head SHA 对齐）：

| 时间 | 构建 | 结论 | head | 根因 |
|---|---|---|---|---|
| 00:15 | #96094 | FAIL | `b544378a`（官方仓空占位分支） | `pull/16259.diff` 0 字节，`checkout-pr` 判空退出 |
| 00:23 | #96105 | FAIL | 同上 | 同上（换 worker 复现，排除单机抖动） |
| 00:46 | #96134 | FAIL | `3d2d9ec9` | G0 知识图谱完整性（CI 侧三位条目号正则，外部） |
| 15:09 | #97085 | FAIL | `e7ada201` | `ln ifmail ifnews`（HMDFS 无硬链接，E079） |
| 19:10 | #97479 | FAIL | `1f461225` | 同上（补丁 0016 尚未推送） |
| **20:58** | **#97651** | **PASS** | **`4e8e7ba5`（含补丁 0016）** | — |
| **21:28** | **#97680** | **PASS** | 同上构建输入（worker CI-011，独立复现） | — |
| 21:28 起 | 排队中 | PENDING | `5321ee75`（仅 notes.md + manifest.yaml 文档回填） | — |

真机 62 项的判定依据：`build()` 末尾的 30 项上游自测与 `test_package` 的 32 项断言，
任一项失败都会让 `conan create` 非零退出并表现为 `L1_RESULT=fail`——这条因果在
#97085/#97479 的真机日志里已被实证（`ln` 失败即 `L1_RESULT=fail: conan create failed`、
`L2/L4/L5=skip: not run`）。#97651 的 `conan-build-test` 与 `Conan test_package` 均为 ✅、
`L1 门禁 (测试执行验证): 通过` ⇒ **真机 62/62 通过**。
逐条 `[pass]` 行属 `conan-build-test` 步骤全文；看板
<https://ohpcd.atomgit.com/ci?id=97651> 默认只渲染 cleanup 步骤（实测抓取该页 62713 B，
对 `UPSTREAM TESTS` / `test_ifmail` / `Testing package` 的 grep 均 0 命中），未取得全文 ⇒
本段"62/62"是**由平台门禁结论推得**，不冒充逐条日志（按证据纪律显式标注推断与实证的边界）。

另：#97651 之后由 `/rebuild` 排的同 SHA 重复构建即 #97680（PASS，换一个 worker 独立复现）；`5321ee75`（文档回填）那一轮在本记录写就时仍在排队，其构建输入与 #97651/#97680 完全相同。

## 7. 已知限制（路径 A，核心能力完整）

1. `USE_NLS=no`：不构建 po/ 下的消息 catalog（需 msgfmt + libintl），交互消息固定英文。
   核心传输/网关/索引功能不受影响。
2. `make_new_ref` 用编译期常量 `REF_DBM=/var/spool/ifmail/refdb`（上游 `main(void)`
   不读配置文件），系统上没有该路径时按上游行为 `exit(2)`；消费者测试把这条当成
   文档化契约断言。
3. 站点配置必须用 `-I <file>` 传入：`etc/ifmail/config.sample` 是上游原样示例
   （`include /etc/ifmail/passwds`、spool 指向 `/var/spool/ifmail`），在新系统上不存在，
   故不作为 CONFIGFILE 装成活配置，避免"看似有配置实则 rc=65"。
4. 编译期路径（CONFIGFILE/MAPTABDIR/DEBUGFILE/LOGFILE/LOCKDIR/PUBDIR/NEWSSPOOL/FAKEDIR）
   烤的是 package_folder（rgb/1.1.1 同法）。若包被搬到别处，`-I` 配置里的
   logfile/debugfile/inbound/outbound/public/nodelist/database 仍可覆盖运行期路径，
   MAPTABDIR 与 CONFIGFILE 无运行期覆盖手段。
5. `readconfig()` 结束时会 `freopen(debugfile,"a",stderr)`：配置之后的所有诊断都进调试
   文件而不是终端；`debugfile` 未配置时落到编译期 DEBUGFILE。测试与排障都要按这一点取证据。
6. ifcico 的串口/modem 拨号路径（termios、UUCP 锁文件、setuid）在本适配中只保证编译与
   链接，未做真机拨号验证；TCP/binkp 与网关、索引路径有测试覆盖。
7. **【推断】** worker 用 bison/3.8.2 + flex/2.6.4.2 生成 parser，本机参考构建用
   Apple bison 2.3 + flex 2.6.4。补丁刻意避开版本相关写法（`YY_SKIP_YYWRAP` 两代 flex 都认；
   `date_lex` 非 static + 显式原型，对 bison 2.x 的隐式声明和 3.x 可能自带的原型都成立；
   两个 .y 都没有 `%expect`，不存在冲突计数不一致的风险）。仍需 CI 首轮回流确认。

## 8. 框架侧发现（写入 feedback）

0. **（最高影响，阻塞所有 PR）`ci/conan/build_and_test.sh` 的 G0b/G0d 用 `E[0-9][0-9][0-9]`
   恰好三位匹配正式条目**，知识库跨过 E999 后：G0b 把 `E1000.kv`…`E1035.kv` 判为
   "非标准命名"，G0d 的 `ls E[0-9][0-9][0-9].kv | wc -l`(999) 与
   `grep -c '^E[0-9]' index.tsv`(1035) 必然不等 ⇒ G0 fail ⇒ `L0/L1/L2/L4/L5` 全部
   `skip: blocked_by_G0`，构建在编译前就终止。修法是把两处模式放宽为 `E[0-9]{3,}`
   （glob 侧 `E[0-9][0-9][0-9]*.kv`）。证据见 §6.1 的对照表。
1. `ohc-run.py refresh-patch --auto` 的 per-file difflib 生成器给 `iflib/parsedate.y`
   产出了 hunk 头行号偏 1 的补丁（`@@ -659,22 +665,26 @@`，而首个上下文行实际在第 658 行），
   conan 的 patch-ng 直接判 `hunk no.2 doesn't match source file at line 659` /
   `source file is different` 并让 G2 失败。改用 `diff -u --label a/<f> --label b/<f>`
   重生成 15 个补丁后，`patch -p1 --dry-run` 与 conan 全部通过。
2. `refresh_patch.py` 的排除清单把 `Makefile` 当构建产物（第 24 行），
   对手写 Makefile 驱动的项目（本包即如此）会**静默丢掉 Makefile 改动**：
   0015 只能手工生成。
3. `templates/conanfile-makefile.py.tmpl` 建议的
   `self.conf.get("tools.build:compiler_executables:c", "clang", check_type=str)`
   在 conan 2.29.1 上抛 `ConanException: [conf] ... does not exist in configuration list`；
   正确写法是取整个 dict 再取键（run-parts/5.23.2、rvvm/0.6、ren/1.0 已是这个形态）。

## 9. 知识沉淀

本次沉淀 2 对草稿（`knowledge/drafts/`，.kv + .md 成对，agent_id 6E98），选题标准是
"换一个软件也会再踩"，两份都做过与 ifmail 无关的最小复现，并跑过
`ohc-run.py draft-review`（质量预检 signature/root_cause/rec 全 ✅，相似度 TOP1
分别只有 0.20/0.23，判定 create）：

1. `DRAFT-ifmail-2.14tx8.10-gdbm-compat-ndbm-no-include-guard`：OHOS 无系统 ndbm，
   只能用 gdbm compat 层；而 compat 的 `<ndbm.h>` **完全没有 include guard**
   （同一 TU 二次包含即 typedef 重定义硬错误），且制品仓 gdbm/1.23 与 1.24 的
   `--enable/--disable-libgdbm-compat` 开关相反，按"选新版本"的直觉会连头文件都拿不到。
   最小复现：单次包含 rc=0、二次包含报错，OHOS clang 15 与宿主 Apple clang 17 一致。
   相近条目 E119（sockaddr_storage 双头重定义，同类不同对，engine 唯一命中）。
2. `DRAFT-ifmail-2.14tx8.10-kr-varargs-clang-error-stub-stdarg`：clang 的
   `<varargs.h>` 是只含 `#error` 的桩头，K&R 的 `va_dcl` + 单参 `va_start(ap)`
   会一次炸出三条硬错误；转换时必须同步 ANSI 原型/static 前置声明/包含顺序，
   且 `-Wno-*` 一类编译选项**完全无效**（不是警告升级，E063 不适用）。
   最小复现：K&R 版 OHOS clang 15 三条错误、Apple clang 17 同样报错；
   C99 版 rc=0 且运行输出 `n=42 s=x`（语义等价，不只是"编过"）。

**命中既有条目（不重复申报）**：**E079**（HMDFS 不支持硬链接，`ln` → `cp`，补丁 0016 直接照其推荐方案执行）；musl 无 `_res` 对象、无 libresolv 私有的
`_getshort/_getlong` —— `grep -in "_res\|resolv" knowledge/graph/index.tsv` 命中
**E516**（"OHOS libc omits _res/__res_state and <linux/ip.h>"，error_signature 含
`undefined symbol: _res|cannot find -lresolv`）。本次按 E516 的口径处置（补丁 0002），
并在 PR 正文"使用知识库"里引用。

**记录但未申报草稿的**（通用性不足或已被既有条目覆盖）：

- musl 无 BSD `re_comp/re_exec`，只有 POSIX `regcomp/regexec`（补丁 0003 包了一层）。
  engine 查重未命中专门条目，但修法就是标准 POSIX 替换，属常识级，不单独立条。
- `readconfig()` 结束时 `freopen(debugfile,"a",stderr)`：这是 ifmail 自身行为，
  只对本包排障/测试取证有用，不具跨软件复用价值。
- flex 生成的 `extern int yywrap(void)` 与项目内 `#define yywrap() 1` 相撞
  （补丁 0011 用 `YY_SKIP_YYWRAP` 解决）。这条**有**跨软件价值（任何老 lex 项目
  都可能踩），本次因 PR 篇幅与查重成本未单独成稿，已在 §4 表格与补丁注释里写清，
  留给后续任务作为候选草稿。
## 10. sysroot 符号级取证（支撑两份知识草稿的前提）

对 OHOS sysroot 的 `usr/lib/aarch64-linux-ohos/libc.so` 做
`llvm-nm -D --defined-only` 逐符号核对（2026-10-17）：

| 符号 | 结果 | 含义 |
|---|---|---|
| `dbm_open` | **0（未导出）** | 证实 OHOS 无系统 ndbm ⇒ 必须走 gdbm compat（草稿 1 的前提） |
| `re_comp` | **0（未导出）** | 证实 musl 无 BSD 正则 ⇒ 补丁 0003 换 POSIX `regcomp/regexec` 是唯一解 |
| `gets` | 1 | `testrfcaddr` 的 `-DTESTING` main 用 `gets()`，真机可链接（否则上游自测第 3 项在 CI 上会链接失败） |
| `vsyslog` | 1 | `loginf/logerr` 的 `HAS_SYSLOG` 分支可用 |
| `regcomp`/`regexec` | 1 / 1 | 补丁 0003 的落点存在 |
| `res_init`/`res_mkquery`/`res_send`/`dn_expand`/`dn_skipname` | 全 1 | `ifroute` 的 MX 查询路径在 musl 上可链接（缺的只是 `_res` 对象与 `_getshort/_getlong`，即补丁 0002） |
| `strcasestr`/`setpgrp`/`setsid`/`statfs` | 全 1 | CONFIG 的 Linux OPTS 块（`NEEDED=strcasestr.o`、`HAS_SETSID`、`HAS_STATFS`）在 OHOS 上成立 |
---

**编译结束**: 2026-10-17 20:08
**最终状态**: built
