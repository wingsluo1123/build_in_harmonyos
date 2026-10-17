# fdm 2.2 — 适配笔记

状态: built

## 一、基本信息

| 项 | 值 |
|---|---|
| 软件 | fdm 2.2（终端邮件过滤/读取器） |
| 上游 | https://github.com/nicm/fdm （tag `2.2`） |
| 源码 | `https://codeload.github.com/nicm/fdm/tar.gz/refs/tags/2.2` |
| sha256 | `75d72794a0a7600c6c007b2f074f75f2852feb688325a7d24fb5dbab68e344ab` |
| 语言 / 构建系统 | C / Autotools（configure.ac + Makefile.am，tag 归档不含 configure） |
| 许可 | ISC（源文件头） |
| 依赖 | tdb/1.4.15、zlib/1.3.1.1、openssl/3.5.6、pcre2/10.48 |
| 构建工具 | automake/1.18、libtool/2.5.4、bison/3.8.2（tool_requires）；autoconf/m4 用 SDK 自带 |

## 二、OHOS 适配要点

### 1. autoreconf 自举与 perl ABI 冲突（本包核心坑）

tag 归档只有 `configure.ac`，需要 `autoreconf -fi` 自举。实测踩到：

```
Can't load '…/perl/5.42.2/…/auto/Cwd/Cwd.so' for module Cwd:
Error relocating …: Perl_my_cxt_init: symbol not found
… at …/p/autom…/p/bin/.aclocal-real line 31
.autoreconf-real: error: …/bin/aclocal failed with exit status: 255
```

根因链（逐条实测）：

1. conan 的 `autoconf/2.72` 会拉入 OHOS 构建的 `perl/5.42.2`，conanbuild 里
   `PERL5LIB` 指向它；而 SDK（`/data/service/hnp/bin/perl`）是 **5.42.0**，
   5.42.0 解释器加载 5.42.2 的 XS（`Cwd.so`）即报 `Perl_my_cxt_init: symbol not found`。
2. **把 conan 的工具 bin 前置到 PATH 无效**：conan automake 包的
   `bin/aclocal`/`bin/automake` 是 `#!/bin/sh` 包装，内部 `exec` 的
   `.aclocal-real` / `.automake-real` 的 shebang **硬编码**
   `#!/data/service/hnp/bin/perl`（`head -1` 实测可见），PATH 顺序改变不了解释器。
3. 反向也不成立：把 `PERL5LIB` 收窄成只含 automake 的纯 Perl 模块目录后，
   conan 的 `.autom4te-real` / `.autoconf-real`（shebang 指向 conan perl）又找不到
   自己的核心模块（`Can't locate strict.pm in @INC … //lib/perl5/5.42.2`）。

⇒ 结论：**不要引入第二个 perl**。配方只 `tool_requires("automake/1.18")` +
`tool_requires("libtool/2.5.4")` + `tool_requires("bison/3.8.2")`，
**不声明 autoconf/m4**（SDK 已有 autoconf 2.72 与 m4）。此时 conanbuild 的
`PERL5LIB` 只有 automake 的 `share/automake-1.18`（纯 Perl，与任何 5.x 兼容），
`autoreconf`/`autoconf`/`autom4te` 走 SDK 的 5.42.0，`aclocal`/`automake` 走
conan 包（硬编码 shebang 也指向 5.42.0）⇒ 全链一个 perl，自举一次通过。

实测对照（三次组合）：conan 全家桶（autoconf+automake+libtool+bison）✗ /
收窄 PERL5LIB + conan autoconf ✗ / **automake+libtool+bison only ✓**；
最终组合 `autoreconf -fi` RC=0，生成 `configure`（201288 B）、`aclocal.m4`、
`Makefile.in`、`etc/{compile,config.guess,config.sub,depcomp,install-sh,missing,ylwrap}`。

### 2. E011：config.status 的 umask 077 临时目录

```
configure 创建 config.status 后，config\.status 报错 could not setup config files machinery
（原文含 can't create ./confXxj9pU/subs1.awk: Permission denied）
```

HMDFS 上 `(umask 077 && mktemp -d "./confXXXXXX")` 建出的目录属主被映射、当前进程
写不进。按 E011 在 **autoreconf 之后**把 configure 里的 `umask 077` 改成
`umask 022`（放前面会被重新生成覆盖）。

### 3. config.guess 认不出 HarmonyOS

`uname` 返回 `HarmonyOS / HongMeng Kernel 1.12.0` ⇒
`configure: error: cannot guess build type; you must specify one`。
显式传 `--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos`。
fdm 无 `AC_TRY_RUN`（只有 `AC_TRY_LINK`/`AC_CHECK_*`），交叉标记下探测全部可用。

### 4. musl 无 REG_STARTEND ⇒ 走上游官方 PCRE2 后端

```
/storage/…/fdm-2.2/re.c:85:43: error: use of undeclared identifier 'REG_STARTEND'
        res = regexec(&re->re, buf, NPMATCH, pm, REG_STARTEND);
```

musl `regex.h` 没有 GNU/BSD 扩展 `REG_STARTEND`。上游 MANUAL「I'm building on Linux
and it complains about REG_STARTEND」一节给出官方出路：**use PCRE**（Debian 与 FreeBSD
端口默认也用 PCRE）。因此 configure 加 `--enable-pcre2`（`-DPCRE2`，编译 `pcre.c`
替代 `re.c`），**零源码补丁、零平台宏**（R8 亦满足）。
`AC_SEARCH_LIBS(pcre2_compile_8, [pcre2-8])` 命中 conan 的 pcre2（静态，
`-DPCRE2_STATIC` 自动注入）。

### 5. configure 的杂项探测结果（实测）

| 探测 | 结果 | 影响 |
|---|---|---|
| `sys/queue.h` | yes | 用系统头 |
| `sys/tree.h` | no | 用上游 `compat/tree.h`（随包） |
| `setproctitle` | no | 不编 setproctitle 调用（`#ifdef HAVE_SETPROCTITLE`） |
| `setresuid` / `setresgid` | yes / yes | — |
| `MREMAP_MAYMOVE` | yes | 用 mremap |
| `strlcpy` / `strlcat` | yes / yes | 不用 compat 实现 |
| `strtonum` | no | 编入 `compat/strtonum.c` |
| `b64_ntop`（含 `-lresolv`） | no / no | 编入 `compat/base64.c`；`-lresolv` 被追加进 LIBS 但 OHOS 可链接，无害 |

## 三、上游测试审计（no_tests）

- `Makefile.am`：只有 `bin_PROGRAMS = fdm`、`dist_fdm_SOURCES`、`CLEANFILES`/
  `BUILT_SOURCES`/`EXTRA_DIST`，**无 `TESTS`、无 `check_PROGRAMS`**；
- 无 `tests/`、`t/` 等测试目录；`configure.ac` 无测试宏；`MANUAL` 无测试章节。
- 实测 `make check` → `make[1]: Nothing to be done for 'check-am'.`（RC=0）。

⇒ `N_static = 0`、`N_registered = 0`、`N_executed = 0`、未执行 0、
`N_consumer = 1`（test_package，4 组 / 19 条断言点，其中第 3 组为端到端核心流程）。

**上游测试用例通过率：不适用（上游无测试，无分母）。消费者测试通过率 100%（4/4 组，19/19 断言点）。**

## 四、消费者测试（test_package，真机实跑）

`test_package/test.sh`（bash 包装，OHOS `/system/bin/sh` 无法直接 exec ELF）共
**4 组 / 19 条断言**，脚本自身打印 `ASSERTIONS: 19 passed, 0 failed`：

1. **随包二进制**（2 条）：`bin/fdm` 存在且可执行位已置；
2. **usage 参数面**（4 条）：真实执行 `fdm -h`，断言打印上游 usage 文本、列出
   子命令 `fetch|poll|cache`、退出码为 1（上游 `usage()` 打印后 `exit(1)`）、
   启动期无 loader 报错；
3. **端到端 fetch → deliver（核心流程，9 条）**：构造本地 maildir 源
   （`src/{cur,new,tmp}` + 一封带 `From`/`Subject`/正文 sentinel 的邮件），规则集
   ```
   account "src" maildir "<src>"
   action "dst" mbox "<dst.mbox>"
   match "^Subject: fdm consumer e2e 2422" in headers action "dst"
   match all action drop
   ```
   真实执行 `fdm -v -f <conf> fetch`，逐条断言：退出码 0；目标 mbox 生成且非空；
   mbox 保留原始 `From`/`Subject` 头与完整正文（body sentinel）；mbox 含 fdm 本次
   投递生成的 `Received: by … (fdm 2.2, account "src")` 痕迹；源 maildir `new/`
   被取空（证明真抓取而非空转）、`cur/` 未被写入；全过程无 loader 报错；
4. **反例对照**（4 条）：同一规则集、换一封 `Subject` 不匹配的邮件，断言退出码 0、
   **目标 mbox 未被创建**、工作目录内不存在该邮件正文的任何落盘副本、
   源 maildir 仍被 catch-all 规则丢弃取空。

**负向对照（把断言改写坏，实测应 FAIL）**：

| 改写 | 实测读数 |
|---|---|
| 第 10 条期望 Subject 改成 `MUTATED-WRONG-SUBJECT` | `[FAIL] #10 mbox 保留原始 Subject 头` / `ASSERTIONS: 9 passed, 1 failed` / rc=1 |
| 第 17 条反例断言反向（要求该 mbox 必须存在） | `[FAIL] #17 不匹配邮件未生成投递目标 mbox` / `ASSERTIONS: 16 passed, 1 failed` / rc=1 |

## 五、平台限制（非配方问题，如实记录；消费者测试的绕法）

### 5.1 当前 uid 不在 `/etc/passwd` ⇒ fdm 连配置都读不到

fdm 在 `main()` 里**无条件**先做 `getpwuid(getuid())`，返回 NULL 即
`fdm: unknown user: 20020084` 并 `exit(1)`（`fdm.c:433-436`）。实测本机
`/etc/passwd` 389 条全是系统账号（root/bin/system/radio/…），交互/构建 uid
`20020084` 没有条目；`/etc` 属 root 不可写、`unshare -r` 被 seccomp 拒
（`Bad system call`）、`sudo -n` 需口令 ⇒ 本平台无法让该调用自然命中。
这是平台账号模型的事实，与构建/配方无关。

**处置**：`test_package/fdm-test-passwd.c` 是只在测试期 `LD_PRELOAD` 注入的极小
垫片，**只补「当前 uid → passwd 条目」这一条缺失**（pw_uid/pw_gid 取真实
getuid/getgid，pw_dir 取 `$FDM_TEST_PWDIR`），其余调用一律不拦截；fdm 的配置解析、
maildir 抓取、正则匹配、动作执行、mbox 投递全部走上游原代码。垫片由 test_package
的 `build()` 用与主配方同一套 conan 工具链编译，只落在 build 目录，
**不进交付产物**（同仓先例：通用机制 M2 的 `redirect_tmp.so` 测试垫片）。

### 5.2 HMDFS 拒硬链接 ⇒ 投递侧用 mbox 而非 maildir

fdm 的 maildir 投递最后一步走 `safemove()` = `link(tmp, new)`（`file.c`）。
实测 HMDFS 上 `link()` 返回 **EPERM**（同目录 `ln` 即 `Operation not permitted`，
`/dev/shm`(tmpfs) 上正常）⇒ maildir 动作停在 `Operation not permitted`；而
`/dev/shm` 又不能建目录/枚举条目（见 `经验文档/OHOS行为探针清单.md` #19–#21）。
**处置**：投递侧改用 mbox 动作（`openlock(O_APPEND)` + write，不依赖 `link()`），
抓取侧仍用 maildir —— 核心流程（抓取 → 匹配 → 投递）与断言强度不受影响。

### 5.3 附：HMDFS 上 `umask 077` 建的目录无法再建子目录

`umask 077; mkdir d; mkdir d/sub` ⇒ `d/sub: Permission denied`（同 E011 家族；
`umask 022` 正常）。本测试规则集不含 maildir 动作、工作目录由 bash 以默认 umask
预建，故不触发；构建期那一处已在配方 `build()` 里按 E011 处理。

## 六、验证结果（真机 conan create）

- `conan create`（干净源码下载 + 自举 + configure + make + make check + install +
  test_package）通过；
- **2026-10-16 返修终跑**：在新建的 `CONAN_HOME=$HOME/tmp/ch/home-fdm`（按 §8 从
  `~/.conan2/remotes.json` 播种 + 追加 `core.sources:download_cache`）上执行
  `conan create archives/f/fdm/2.2 -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64
  --build=fdm/* --build=missing`，**一次跑完「本地从源码构建 + test_package」**
  （16:11:11Z → 16:13:57Z）：`rc=0`，日志内 `fdm/2.2: Building from source` →
  `Created package revision …` → `ALL TESTS PASSED` /
  `ASSERTIONS: 19 passed, 0 failed`（4/4 组）。成功路径自动清理测试工作目录，
  配方目录不留残余制品；
- 产物：`bin/fdm`（ELF 64-bit LSB arm64, dynamic, `/lib/ld-musl-aarch64.so.1`）、
  `share/man/man1/fdm.1`、`share/man/man5/fdm.conf.5`、`licenses/README`；
- 74 个上游 `.c` + `compat/{base64,strtonum}.c` + bison 生成的 `parse.c` + `lex.c`
  全部编译通过（仅 OpenSSL 3.0 弃用属性告警，无错误）。
---

**编译结束**: 2026-10-15 03:01
**最终状态**: built
**返修**: 2026-10-16（rule8：上游 N=0 且适配后 M=0 ⇒ 补 4 组 / 19 条断言的消费者测试，
其中第 3 组为端到端 fetch → deliver 核心流程；终跑 rc=0）
