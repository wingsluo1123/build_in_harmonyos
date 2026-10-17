# ircd-ircu 2.10.12.19 适配笔记（HarmonyOS PC / OHOS aarch64）

## 上游与版本

- **软件**：ircd-ircu（Undernet IRC daemon，ircu2）
- **上游 tag**：`u2.10.12.19`，`include/patchlevel.h` 里 `BASE_VERSION="u2.10"` +
  `RELEASE=".12."` + `PATCHLEVEL "19"`，所以 `ircd -v` 打印 `ircd u2.10.12.19`。
- **源码源**：<https://github.com/UndernetIRC/ircu2/releases/download/u2.10.12.19/ircu2.10.12.19.tar.gz>
  sha256 `79e3264b36c093c1f7c7019511b8ab7d3f0c16086c8b8b2f07463b7bd3787334`
  （独立下载两次校验一致）。

### 为什么不是 github.com/ircu/ircu

原始 ircu 项目已经停摆，实测：

| 候选 | 实测结果 |
|------|----------|
| `https://ircu.org/` | DNS/连接失败（curl 返回码 000） |
| `https://github.com/ircu/ircu` | HTTP 404，API 也返回 `{"message":"Not Found"}` |
| `https://github.com/UndernetIRC/ircu2` | tag `u2.10.12.19` + release 资产 `ircu2.10.12.19.tar.gz` ✔ |

Undernet IRC 是 ircu2 的现役维护方；Debian 源码包 `ircd-ircu` 的
`2.10.12.19+dfsg` 也正是从这一版本派生（`sources.debian.org/api/src/ircd-ircu/`
可见 `2.10.12.19+dfsg-1/3`），因此 GitHub release 资产是权威源，满足 R39。

## 构建系统

autoconf（`./configure` + 手写递归 Makefile，`SUBDIRS = ircd ircd/test`）。
`./configure --help` 的可选包只有 `--with-leak-detect / ipv6 / symlink / mode /
owner / group / domain / chroot / dpath / cpath / lpath / maxcon`——
**没有任何第三方库选项**。

`configure.in` 的全部外部探测：

```
AC_SEARCH_LIBS(crypt, descrypt crypt, , ...)
AC_CHECK_HEADERS(crypt.h poll.h inttypes.h stdint.h sys/devpoll.h sys/epoll.h
                 sys/event.h sys/param.h sys/resource.h sys/socket.h)
AC_CHECK_FUNCS([kqueue setrlimit getrusage times])
```

密码学后端（`ircd_crypt_plain.c` / `ircd_crypt_smd5.c` / `ircd_crypt_native.c`）
全部随源码分发，所以本包 **`requires` 为空**，W0 依赖发布检查天然通过。

## 踩坑与处置

> 编号说明：2026-10-14 AI 检视指出本节原先从 4 直接跳到 6（历史上从未有过第 5 节），
> 已把原 6..12 顺延为 5..11。文中其它位置若引用旧编号，以标题文字为准。

### 1. config.guess / config.sub 是 2005 年的，认不出 aarch64 和 OHOS（E007）

tarball 自带的 `config.guess`（`timestamp='2005-12-23'`）与 `config.sub` 早于
aarch64 出现。实测未打补丁时：

```
$ ./config.sub aarch64-linux-ohos
Invalid configuration `aarch64-linux-ohos': machine `aarch64-linux' not recognized
```

两个补丁：

- `patches/0001-config.guess-ohos.patch`：在 `case "${UNAME_MACHINE}:${UNAME_SYSTEM}:..."`
  顶部加 `*:OHOS:*:* | *:HarmonyOS:*:*` 分支，输出 `<machine>-unknown-linux-ohos`。
- `patches/0002-config.sub-ohos-aarch64.patch`：四处改动
  1. `case $maybe_os` 增加 `linux-ohos*`（否则 `aarch64-linux-ohos` 会被拆成
     `basic_machine=aarch64` / `os=-linux`）；
  2. CPU 表增加 `aarch64`；
  3. OS 归一化白名单增加 `-linux-ohos*`；
  4. 在 `-linux*`（会被 sed 改写成 `linux-gnu`）之前插入 `-linux-ohos*)` 分支。

打补丁后实测（无回归）：

| 输入 | 未打补丁 | 打补丁后 |
|------|----------|----------|
| `aarch64-linux-ohos` | Invalid configuration | `aarch64-unknown-linux-ohos` |
| `aarch64-unknown-linux-ohos` | Invalid configuration | `aarch64-unknown-linux-ohos` |
| `aarch64-linux-ohos6.0` | Invalid configuration | `aarch64-unknown-linux-ohos6.0` |
| `x86_64-linux-ohos` | Invalid configuration | `x86_64-pc-linux-ohos` |
| `x86_64-pc-linux-gnu` | `x86_64-pc-linux-gnu` | `x86_64-pc-linux-gnu`（不变） |
| `i686-pc-linux-gnu` | 正常 | 正常 |

> **补丁写法上的一个坑**：`-linux-ohos*` 加进 OS 白名单时**不能**顺手把那条
> `|` 分隔的 case pattern 列表折成两行。折行后 `dash`（WSL 上 `/bin/sh` 就是
> dash，autoconf 就是用它跑 config.sub）解析整个 `case` 直接报
> `1210: Syntax error: word unexpected (expecting ")")`，bash 同样报
> `syntax error near unexpected token '|'`。补丁必须保持单行。

**为什么 CI 上没被这段卡住**：`AutotoolsToolchain` 只在
`cross_building()` 为真时才传 `--host`。本地门禁与 CI 都用同一份 profile
做 `-pr:h` / `-pr:b`（都是 `ci/conan/profiles/ohos-aarch64`），两者相同 →
不传 `--host` → autoconf 走原生路径，config.sub 根本不会被调用。补丁是为
「真正的交叉构建」（`-pr:b` 与 `-pr:h` 不同）准备的，config.guess 则每次
configure 都会跑。两个补丁都通过 `apply_conandata_patches` 注册并在
`build()` 里应用，属于必需的 portability 补丁而非平台宏 hack（符合 R8）。

### 2. musl 完全没有 `getpass(3)`，`umkpasswd.c` 在 OHOS 上根本编译不过

这是**唯一一个真正的 libc 缺口**（不是 autoconf 老旧那类）。实测 OHOS 的
musl sysroot：

```
$ grep -rl getpass <ohos-sysroot>/usr/include | wc -l
0
```

`ircd/umkpasswd.c` 只 `#include <unistd.h>` 就直接调 `getpass("Password: ")`。
musl 从未实现过这个 POSIX 遗留函数，于是 clang 15 直接报错：

```
umkpasswd.c:452:8: warning: call to undeclared function 'getpass'
umkpasswd.c:452:6: error: incompatible integer to pointer conversion
                          assigning to 'char *' from 'int'
make[1]: *** [Makefile:236: umkpasswd.o] Error 1
```

`patches/0003-umkpasswd-getpass-musl.patch` 就地实现一份等价的
`ircu_getpass()` 并改调它。两个语义细节是刻意这么定的，都实测过：

- **只有 stdin 是终端时才去开 `/dev/tty` 并关回显**（`isatty(fileno(stdin))`
  为真才开）。否则 `fopen("/dev/tty","r+")` 在有控制终端的环境里会成功，
  于是「`printf pw | umkpasswd -m plain`」这种批用法会去读**没人看着的终端**
  并一直阻塞。CI worker 上 `conan create` 由 setsid 启动、没有控制终端，
  `/dev/tty` 打开失败才恰好没出事——换个启动方式就会挂到 45 分钟构建超时。
- **永不返回 NULL**，和 `getpass(3)` 一致。调用方是
  `pw = getpass(...)` 之后无条件解引用，而本构建带 `-DNDEBUG`（`assert`
  被编掉），一旦返回 NULL 就是 `strlen(NULL)` 段错误。EOF 时返回空串缓冲区。

实测（都在有 `/dev/tty` 的环境下）：

| 输入 | 结果 |
|------|------|
| `-m plain conanprobe` | `Crypted Pass: $PLAIN$conanprobe`，rc 0 |
| `printf 'conanprobe\n' \| -m plain` | 同上，rc 0，**不阻塞** |
| `-m plain < /dev/null` | `Crypted Pass: $PLAIN$`，rc 0（空口令，不崩） |
| 200 字符口令 | 截到 127 字节，rc 0 |

返回的是静态缓冲区，所以调用方 `memset(pw, 0, strlen(pw))` 擦口令依然合法。

> **连带现象，别误判成第二个 bug**：第一次跑时日志里还有一条
> `ircd/test/ircd_string.c:39: fatal error: 'chattr.tab.c' file not found`。
> 那不是独立缺陷——`ircd` 子目录的 `make` 因为 `umkpasswd.o` 编译失败提前
> 中止，`chattr.tab.c: table_gen` 规则没跑到，`ircd/test` 才在
> `#include "chattr.tab.c"` 上挂掉。修好 getpass 就一起消失了。

### 3. tarball 不含生成后的 lexer / parser → flex、bison 是硬依赖

`ircd/Makefile.in` 的 `SRC` 里列了 `lex.yy.c` 和 `y.tab.c`，但 tarball 里只有
`ircd_lexer.l` / `ircd_parser.y`，生成的 `lex.yy.c`、`y.tab.c`、`y.tab.h`、
`chattr.tab.c` **全部缺失**（`find` 只找到 `ircd/table_gen.c`）。对应规则：

```
lex.yy.c: ircd_lexer.l y.tab.h      → ${LEX}
y.tab.c y.tab.h: ircd_parser.y     → ${YACC} -d
chattr.tab.c: table_gen            → ./table_gen > chattr.tab.c
```

CI 机器上没有系统级 flex/bison，所以按 `archives/c/canlock/3.3.1`、
`archives/c/captagent/6.4.4` 的既有做法用 `tool_requires` 补齐：

```python
self.tool_requires("flex/2.6.4.2")
self.tool_requires("bison/3.8.2")
```

（必须是 `flex/2.6.4.2` 而不是 `flex/2.6.4`：后者只带 `libfl.a` +
`FlexLexer.h`，根本没有 `bin/flex`，`AC_PROG_LEX` 找不到。）

两者都已发布到 `ohpcd`（W0 用 `conan download "<pkg>" -r=ohpcd --only-recipe`
验证过，见交付证据）。Conan 2 会把 tool_requires 的 `bindirs` 自动放进
构建环境 PATH，autoconf 的 `AC_PROG_LEX` / `AC_PROG_YACC` 因此能直接找到。

`table_gen` 是用 `$(CC)` 编译的 **aarch64 OHOS** 宿主工具，构建时需要执行它。
CI worker 本身就是 aarch64 的 HarmonyOS 设备（profile 里
`PATH=+(path)/data/service/hnp/bin`），所以原生可跑。

`bison/3.8.2` 这个包本身有两处路径被烘死了（`PKGDATADIR=/share/bison`、
m4 程序 `/data/service/hnp/bin/m4`）。`build()` 里按「实际在 PATH 上的 bison」
推导 `BISON_PKGDATADIR`；`M4` 则**无条件**换成 `_usable_m4()` 实测能跑通一个
真实 m4 程序的那个（原因见第 11 条：m4 驱动失败时 bison 仍退出 0，会把失败
推迟到链接期，报成完全不相干的 `undefined symbol`）。

### 4. tarball 带着打包者机器上的 Makefile / config.status / config.h（构建漂移）

tarball 里同时存在 `Makefile`、`ircd/Makefile`、`ircd/test/Makefile`、
`config.status`、`config.h`、`config.log`、`stamp-h`——都是 2019 年打包者在
自己机器上 `./configure` 的产物，**mtime 与所有 `.in` 模板完全相同**。
`Makefile: Makefile.in config.status` 这类规则在 mtime 相等时不会被 make 触发，
一旦命中就会拿打包者的 `prefix=/usr/local` 去构建。

`source()` 因此显式清理这批产物，强制 `./configure` 从 `.in` 模板全部重建：

```python
STALE_BUILD_PRODUCTS = (
    "Makefile", "config.status", "config.log", "config.h", "stamp-h",
    os.path.join("ircd", "Makefile"), os.path.join("ircd", "test", "Makefile"),
)
```

另外 `ircd/version.c` 也是随包预生成的，但它的规则带 `.PHONY`，每次都会用
`version.c.SH` 重新生成，不受影响。

### 5. 必须在源码树内构建（VPATH 不干净）

顶层 `Makefile.in` 里有 `config.status: configure` 这种规则，但顶层 Makefile
**没有定义 `VPATH`**（只有子目录 `ircd/Makefile.in` 有
`VPATH = @srcdir@`）。VPATH 构建时 make 在构建目录找不到 `configure`。
所以 `layout()` 里把 build 目录直接指回源码目录：

```python
basic_layout(self, src_folder="src")
self.folders.build = self.folders.source
```

### 6. `make install` 不能用：`${DESTDIR}` 被忽略 + 宿主 `strip` 读不懂 aarch64

`ircd/Makefile.in` 的 `install-no-symlink` 规则是：

```make
${INSTALL} -m ${IRCDMODE} -o ${IRCDOWN} -g ${IRCDGRP} ircd ${BINDIR}/ircd
${INSTALL} -s -m 700 -o ${IRCDOWN} -g ${IRCDGRP} umkpasswd ${BINDIR}
${INSTALL} -s -m 700 -o ${IRCDOWN} -g ${IRCDGRP} convert-conf ${BINDIR}
${INSTALL} -m 600 -o ${IRCDOWN} -g ${IRCDGRP} ${top_srcdir}/doc/example.conf ${DPATH}
```

两个独立的坑：

1. **没有 `${DESTDIR}` 前缀。** `Autotools.install()` 只是给 `make` 加
   `DESTDIR=<package_folder>`，而上面四条规则一个都没用它。Conan 又传
   `--prefix=/`，于是 `${BINDIR}` = `//bin`，`ircd` 被装到**构建机真实的
   `/bin`**。本地实测留下了一个 954 KB 的 `/usr/bin/ircd`，而 Conan 包里
   仍然是空的（`package(): WARN: No files in this package!`）。
2. **`-s` 结尾是宿主 `strip`。** x86 构建机上的 GNU `strip` 认不出 aarch64
   ELF：`strip: Unable to recognise the format of the input file '//bin/umkpasswd'`
   → `install process terminated abnormally` → `Error 1`。

   更阴的是顶层 `Makefile` 的 install 目标用
   `@for i in ${SUBDIRS}; do cd $$i; ${MAKE} install; cd ..; done`，
   循环体最后一条是 `cd ..`（恒成功），所以**子目录失败不会让
   `make install` 返回非零**，`Autotools.install()` 也不会抛异常。

所以 `package()` 改成显式 `copy()` 四个产物并 `chmod 0755`：

```python
for binary in INSTALLED_BINARIES:      # ircd / umkpasswd / convert-conf
    copy(self, binary, src=os.path.join(self.source_folder, "ircd"), dst=pkg_bin)
    os.chmod(os.path.join(pkg_bin, binary), 0o755)
copy(self, "example.conf", src=os.path.join(self.source_folder, "doc"),
     dst=os.path.join(self.package_folder, "ircd"))
```

顺带解决 HMDFS 上「build 树能跑、打包后 EPERM(Errno 1)」的通病：
`copy()` 会重新落一次权限位。

`--with-dpath` 仍然显式钉在包目录内（`<pkg>/ircd`）：它是 ircd 编译进去的
**默认数据目录**，上游默认是 `$libdir`，在 `--prefix=/` 下就是 `/lib`。

### 7. `--bindir` 决定 `SPATH`，不钉住 `ircd` 启动就自杀

`configure.in` 把 `SPATH`（ircu `/restart` 用的自身路径）算成
`$bindir/ircd`。Conan 默认 `--bindir='${prefix}/bin'` + `--prefix=/`
→ `SPATH="//bin/ircd"`，指向构建机的 `/bin/ircd`，不存在。于是 `ircd -k`
和守护进程都在启动检查处退出：

```c
if (!check_file_access(SPATH, 'S', X_OK) || !check_file_access(configfile, 'c', R_OK))
    return 4;
```

autoconf 对 `--bindir` 是「最后一个生效」，所以在 toolchain 默认值之后追加
`--bindir=<package_folder>/bin`，`SPATH` 就正好指向本配方真正装出来的产物。

`--with-symlink=no` 也顺带影响 `SPATH`：`symlink=no` 时 configure 取
`$bindir/ircd`（而不是 `bin/ircd.<日期>`），`check_file_access` 才有的可查。

### 8. `MAXCONNECTIONS` 取自**构建机**的 `ulimit -Hn`，会把守护进程焊死

`configure.in` 在没有任何 `--with-maxcon` 时：

```sh
unet_maxcon=`ulimit -Hn`
...
unet_maxcon=`expr $unet_maxcon - 4`
AC_DEFINE_UNQUOTED(MAXCONNECTIONS, $unet_cv_with_maxcon, ...)
```

也就是说这个编译期常量取决于**跑 configure 的那台机器**。本机
`ulimit -Hn = 1048576` → `MAXCONNECTIONS = 1048572`，远超
`numnicks.c` 自己的硬上限 `NN_MAX_CLIENT = 64^3 = 262144`，于是每一次
`ircd` 调用（连 `ircd -k` 之后启动守护进程那一步）都在启动时自杀：

```
MAXCLIENTS (or MAXCONNECTIONS) is (at least) 786432 too large !
Please decrease this value.
```

`1048576 - 262144 = 786432`，和消息里的数字完全对上。显式钉死：

```python
MAX_CONNECTIONS = 1024
tc.configure_args.append(f"--with-maxcon={MAX_CONNECTIONS}")
```

1024 既远低于 262144 的硬上限，也远低于消费者实际会有的 `RLIMIT_NOFILE`；
顺带把 `LocalClientArray[MAXCONNECTIONS]` 从 8 MB 降到 8 KB。
test_package 另外断言 `ircd -v` 打印的编译上限 `<= 262144`，防止这个值再被
构建机环境带偏。

### 9. `--with-symlink=no`：避开 `bin/ircd.<时间戳>` + 软链接方案

默认的 `install-with-symlink` 规则会把二进制装成
`${BINDIR}/ircd.$(date +%Y%m%d%H%M)` 再建一个名为 `ircd` 的相对软链接，
还会往 `/tmp/ircd.tag` 写临时文件。Conan 包不适合带这种运行时生成的软链接，
`--with-symlink=no` 切到 `install-no-symlink`，直接装成 `${BINDIR}/ircd`。

`--with-mode=755` 覆盖上游默认的 `0711`，让包里产物对所有使用者可读可执行。

### 10. autoconf 2.64 的 `umask 077` 暂存目录在 HMDFS 上不可用 → `config.status` 死

真机 CI（构建 #79140 / worker CI-020，以及更早的 #73461、#73463）里 configure
一路跑到最后一步才死，`config.log` 里留下：

```
checking max connections... 1024
configure: creating ./config.status
./config.status: line 610: ./confhoCbLA/subs1.awk: Permission denied
config.status: error: could not setup config files machinery
ConanException: Error 1 while executing
```

`./confhoCbLA/` 是 autoconf 2.64 自己建的暂存目录（`configure` 第 7722 行、
即它生成 `config.status` 的那段模板）：

```sh
{
  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
  test -n "$tmp" && test -d "$tmp"
}  ||
{
  tmp=./conf$$-$RANDOM
  (umask 077 && mkdir "$tmp")
} || as_fn_error "cannot create a temporary directory in ." "$LINENO" 5
```

紧接着 config.status 就往 `$tmp/subs1.awk` 写替换脚本（对应 tarball 自带的
`config.status` 第 610 行；补丁只改 `configure`，因为 `source()` 已经把 tarball
里那份预生成的 `config.status` 删掉了）。在鸿蒙 worker 的 HMDFS 上，这个按
`umask 077` 建出来的目录建完就写不进去，于是 `config.status` **一步都没往下走**，
配置文件（`Makefile` / `config.h` / `ircd.conf` 等）一个都没生成 ——
`ConanException: Error 1` 只是这个的表面症状。

`077` 在这里没有任何收益：暂存目录只装本次 configure 生成的 AWK 替换/宏定义
脚本，退出时由 trap `rm -fr` 删掉。`patches/0004-configure-umask-022.patch` 把
两处 `umask 077` 改成 `022`。本仓已合并的多个配方用的是同一条修法
（`archives/a/adns/1.6.2`、`archives/a/activity-log/0.9.7`、
`archives/a/adms/2.3.7` …），本地 WSL（ext4）复现不出来，属 worker-only 缺陷。

> **顺带一条别误判的日志**：`checking max connections... 1024` 前面还有一行
> `expr: Unexpected extra input '4'`。它是 `configure` 第 6960 行
> `unet_maxcon=\`expr $unet_maxcon - 4\`` 来的 —— worker 上 `ulimit -Hn` 返回空，
> 于是 `expr  - 4` 报了个多余的 `4`。因为配方**显式钉了** `--with-maxcon=1024`
> （第 8 条），`unet_cv_with_maxcon` 在下一段就被覆盖，结果仍是 1024，这条消息
> 无害。它同时也是第 8 条那个「编译期常量取自构建机」缺陷的现场证据。

### 11. bison 驱动不了 m4 时**静默**产出空 `y.tab.c` → 链接期 `undefined symbol: yylval / yyparse`

真机 CI（构建 #79156，worker CI-037）configure、编译全部正常，唯独 `ircd` 最后一步链接挂：

```
bison -y -d ./ircd_parser.y
/data/service/hnp/bin/clang ... -c y.tab.c -o y.tab.o
flex ./ircd_lexer.l
...
ld.lld: error: undefined symbol: yylval
>>> referenced by lex.yy.c
>>>               lex.yy.o:(yylex)
ld.lld: error: undefined symbol: yyparse
>>> referenced by s_conf.c
>>>               s_conf.o:(read_configuration_file)
clang-15: error: linker command failed with exit code 1
make[1]: *** [Makefile:241: ircd] Error 1
```

**这条报错指错了地方**：`yylval` / `yyparse` 由 bison 生成的 `y.tab.c` 定义
（实测本机 bison 3.8.2 在 `y.tab.c` 第 1844/1856 行生成 `YYSTYPE yylval;` 与
`yyparse`）。两个符号同时缺失 = `y.tab.o` 里根本没有解析器。但日志里
`clang -c y.tab.c -o y.tab.o` **一行错都没有** —— 因为一个**空的 `y.tab.c`
是合法 C**，编出来就是空 `y.tab.o`，错误只能推迟到链接期暴露。

#### 根因：bison 只检查 m4 的退出码，m4 出问题它照样退出 0

`ircd/Makefile.in` 的规则是 `${YACC} -d ${srcdir}/ircd_parser.y`，而 bison 把
骨架文件喂给 m4 再收 stdout。本地实测（`bison 3.8.2`）：

| m4 行为 | bison 退出码 | y.tab.c |
|---|---|---|
| 正常 GNU m4 | 0 | 135 KB，含 `yyparse` / `YYSTYPE yylval;` |
| 读完输入、**什么都不输出**、exit 0 | **0** | **没有 / 空** |
| 中途 `head -20` 后 exit 0 | 141（SIGPIPE） | 无 |

即「m4 悄悄不产出」这一种，bison **既不报错也不返回非零**，`make` 认为规则成功。
worker 上 `bison/3.8.2` 二进制里烘死的 m4 程序是 `/data/service/hnp/bin/m4`；
原配方为了「不写死路径」，只在**该路径不可用**时才覆盖 `M4`
（`os.path.isfile() and os.access()`）。可执行位存在 ≠ 这个 m4 能把活干对，
于是 worker 上 bison 全程用那个 m4，产出的解析器是空的，失败被推迟到了链接期。

> **别把 `m4/1.4.19` 在本机 qemu 下跑不起来当成设备也跑不起来。** 本地 WSL
> 用 qemu-aarch64 跑 OHOS 产物时 guest musl **没有预载 fortify shim**，会打印
> `Error relocating .../m4: __strchr_chk: symbol not found`；这是**本地环境**
> 缺口（本仓 T137/T167），真机 libc 导出完整 45 个 `_chk` 符号，同一二进制在
> worker 上原生可跑。

#### 处置

1. `build_requirements()` 显式 `tool_requires("m4/1.4.19")`：让「bison 用的 m4」
   在所有 host 上都是同一个已知的 GNU m4（`flex/2.6.4.2` 虽已传递引入它，
   但显式声明才是本配方可依赖的契约；制品仓 `m4/1.4.19` 已发布，
   `conan download` 可验证）。
2. `_usable_m4()`：**不看文件存在性，直接拿真实 m4 程序实测**——
   `define(\`ircd_probe',\`m4-ok')ircd_probe` 喂给它，只有退出码 0 且输出里出现
   `m4-ok` 才算可用；按 PATH 顺序挑第一个真能跑的。设备上第一个就是
   `m4/1.4.19`，本地 WSL 上它会因 guest shim 缺失被跳过、回落到系统
   `/usr/bin/m4`，两边都能构建。
3. `_check_parser_generator()`：在 `make` **之前**用同一个 bison+m4 显式生成
   `ircd/y.tab.c`（`M4=... bison -y -d ircd_parser.y`），然后断言文件非空且
   正文含 `yyparse`。这样万一将来 m4 再退化，报错会指名 bison 和 m4，
   而不是几万行之后的 `undefined symbol`。生成后的 `y.tab.c/y.tab.h` 比
   `ircd_parser.y` 新，`make` 不会重复生成。
4. `make` 也要拿同一个 m4：**flex 2.6.4 同样要 m4** 展开自己的 skeleton
   （`ircd_lexer.l` → `lex.yy.c`）。m4 不能跑时 flex 会留下**0 字节的
   `lex.yy.c`** 并以 `Error 141` 退出——和 bison 是同一个静默模式，只是它至少
   返回非零。实测 `flex` 认的是 **`M4` 环境变量**（`strings flex` 里能看到
   构建时烘进去的 m4 路径），但**只把 `M4` 写进 `os.environ` 不够**：Conan 在
   每次 `self.run()` 前后会应用/还原 `conanbuild` 环境，`os.environ` 里的改动
   到不了 `make` 子进程。因此改成把 m4 作为 **make 命令行变量**
   （`autotools.make(args=["M4=..."])`）传入：GNU make 会把命令行变量导出进每一条
   recipe 的环境，flex / bison 正是在那里读 `M4`。

根因验证（本地实测）：

- `M4=<读完输入什么都不输出、exit 0 的脚本> bison -y -d ircd_parser.y` → `rc=0`
  且根本没有 `y.tab.c`；换成正常 m4 → 135 551 字节且含 `yyparse`。
- `PATH=<m4/1.4.19 的 bin>:$PATH`（本地 qemu 下那个 m4 因 guest shim 缺失起不来）
  跑 `flex ircd_lexer.l` → `rc=141`、`lex.yy.c` 大小 **0**；
  同一 PATH 上加 `M4=/usr/bin/m4` → `rc=0`、`lex.yy.c` 50 314 字节。

#### 预防

- 任何「代码生成工具（bison/flex/yacc）在 `build()` 里跑」的配方，**不要用
  「文件存在 / `--version` 能跑」判断工具可用**：这类工具普遍把子进程 m4 的
  失败吞掉并返回 0。要么实测一次真实输入输出，要么在生成后断言产物内容。
- 看到链接期 `undefined symbol` 指向「本该由代码生成器产出的符号」时，
  第一反应应是**回头看生成器那一步的日志**，而不是去改链接参数。
- `bison` 的 `M4`/`BISON_PKGDATADIR` 用**实际在 PATH 上的 bison** 推导，
  别写死；同时必须真的验证那个 m4 能干活。

## 上游测试

ircu2 **没有** `make check` / `make test` 目标（顶层 `Makefile.in` 的目标只有
`all/build/config/clean/distclean/install/uninstall/depend/maintainer-clean/
indent/update`）。`tests/` 目录里的 `test-driver.pl` 需要 CPAN 的
`POE` + `POE::Component::IRC`，要拉起两个真实 ircd 实例并 `sleep 610` 等
IPcheck 落盘，不适合 CI。

真正可执行的上游测试是 `ircd/test/` 下的 4 个 C 单元测试程序——它们被顶层
`all` 目标编译（`SUBDIRS = ircd ircd/test`）却没有任何目标调用它们：

| 程序 | 源码 | 测什么 |
|------|------|--------|
| `ircd_chattr_t` | `ircd/test/ircd_chattr_t.c` | channel attribute 位图解析 |
| `ircd_in_addr_t` | `ircd/test/ircd_in_addr_t.c` | `ircd_in_addr_t` 构造（v4/v6） |
| `ircd_match_t` | `ircd/test/ircd_match_t.c` | IRC glob 匹配 |
| `ircd_string_t` | `ircd/test/ircd_string_t.c` | `unique_name_vector` 等字符串工具 |

`build()` 在 `make` 之后逐个执行它们，断言**退出码为 0 且输出非空**
（只看退出码不够——这些程序 `main()` 结尾都是 `return 0`）。
这一步同时给 CI 的 L1b 提供「测试真实编译并运行」的日志证据。

## test_package（消费者视角）

`test_package/test.sh` 对装好的产物做真实功能验证：

0. **先钉住来源**：断言 `command -v ircd` 落在 `.conan2/` 包目录内。
   （第一次跑时 `package()` 还没修好，包是空的，于是 `ircd` 被解析成构建机上
   被上游 `make install` 污染出来的 `/usr/bin/ircd`，测试「通过」了一个根本不是
   本包产物的二进制。这条断言就是为了堵住这个假绿。）
1. `ircd -v` → 断言 `ircd u2.10.12.19`、事件引擎列表、连接上限；
2. `ircd -?` → 断言用法文本、`Server not started.`、非零退出码；
3. `ircd -k` → 用生成的配置走一遍真实配置解析器，断言 `checked okay`；
4. **反向用例**：故意写坏的配置必须被 `ircd -k` 拒绝（证明第 3 条不是恒真）；
5. 真启动 `ircd -n`，**连 `server = no` 的客户端端口**，用 bash `/dev/tcp` 发
   `NICK`/`USER`、按 ircu2 的 cookie 探针回 `PONG <cookie>`，完成 IRC 注册，
   断言收到 `001 RPL_WELCOME`、`004 RPL_MYINFO`（且 004 里带
   `u2.10.12.19`）、`005 RPL_ISUPPORT`；另外断言 `server = yes` 端口拒绝
   客户端注册；发 `QUIT` 后服务端断开；
6. `SIGTERM` 干净退出（exit 0）且端口释放；
7. 附带的 `convert-conf` 能解析配置；
8. `umkpasswd`：`-l` 能列出 `plain` 机制；`-m plain <口令>`（命令行给口令）
   与 `printf 'x\n' | umkpasswd -m plain`（**走补丁里的无回显读入**）都能产出
   `Crypted Pass: $PLAIN$...`，且两者结果一致——这三条正好把 `patches/0003`
   改写的代码路径真正跑起来；
9. 上游 `doc/example.conf` 已随包装到 `<pkg>/ircd/example.conf`。

### ircd 的注册握手有两个非 RFC 细节，测试必须照做

1. **客户端必须连 `server = no` 的端口。** 配置里
   `Port { server = yes; port = A; }` 只说服务器互联协议；往那里发
   `NICK`/`USER` 会被 `m_user.c` / `m_nick.c` 的 `IsServerPort()` 拒掉：

   ```
   ERROR :Closing Link:  by ohos-conan-test.example.net (Use a different port)
   ```

   很容易误判成「守护进程没起来」——端口明明在 listen。测试因此连
   `server = no` 的那个端口，并额外断言 `server = yes` 端口确实拒绝客户端注册。
2. **`PING :<cookie>` 必须回 `PONG <cookie>`，不能是 `PONG :<cookie>`。**
   ircu2 在放行注册前先发一个 cookie 探针和 numeric 513：

   ```
   PING :3960781614
   :ohos-conan-test.example.net 513 conanprobe :To connect, type /QUOTE PONG 3960781614
   ```

   `s_auth.c: auth_set_pong()` 把 PONG 的参数当无符号整数和 cookie 比
   （`if (cookie != auth->cookie)`），带冒号就永远不等。照做之后就能拿到完整的
   numeric 突发（001/002/003/004/005/251/255/422 + MODE）。

### ircd 拒绝以超级用户身份运行 → `test_package/droproot.c`

`ircd.c` 的 `set_userid_if_needed()` 只要 `uid/euid/gid/egid` 有一个是 0 就
打印 `ERROR:  This server will not run as superuser.` 并让 `main()` 返回 3，
`-k` 也一样。

- OHOS CI worker 本身就跑在 HMDFS 映射出来的普通 uid 上（同一台机器上实测
  `euid=20020101`、文件属主 `20001006`），**不需要任何处理**；
- 本地门禁跑在 WSL root 上，所以 `test_package/conanfile.py` 的 `build()` 会把
  `droproot.c` 编出来：先试 `unshare(CLONE_NEWUSER)` + `uid_map`（内核访问控制
  会反向映射回外层 uid，文件权限不受影响），失败再退回 `setgid`/`setuid`，并在
  退回路径上给两个可执行文件的上层目录补 `S_IXOTH`（只加「可进入」，不加可读，
  否则 0700 的 `$HOME` 下的 conan 包目录对降权后的进程不可见）。
  uid 本来就非 0 时它原样 `execvp`。

`.gitignore` 里加了 `archives/i/ircd-ircu/*/test_package/droproot`
（比照 `archives/n/nss/*/test_package/test_nss` 的既有做法），因为
`conan create` 每次都会在 `test_package/` 里重新生成它。

> **shell 选择**：OHOS 的 `/system/bin/sh` 是 mksh，既跑不了 ELF 也没有
> `/dev/tcp`。`test_package/conanfile.py` 因此在运行时按
> `CONFIG_SHELL` → `/data/service/hnp/bin/bash` → `PATH` 里的 `bash` 逐个探测，
> 而不是把路径写死（本地门禁环境里 `/data/service/hnp/bin/bash` 是指向
> `/bin/bash` 的软链，两条路径都可用）。

## 门禁结果与两处「按设计不绿」的解释

本地同源门禁（`CI_PACKAGES=archives/i/ircd-ircu/2.10.12.19 zsh ci/conan/build_and_test.sh`）：
G0 / L0 / L1 / KC / JC / L5 全 pass。剩下两条是**设计上就不该变绿**的，记在这里
免得下次有人以为漏了什么：

### L2 = skip：ircu2 没有 `--version` / `--help`

L2 逐个跑 `bin/*` 的 `--version`，失败再试 `--help`，只要有一个退出 0 就算 pass。
实测三个二进制的**真实**退出码：

| 二进制 | `--version` | `--help` | 该项目有的等价物 |
|--------|-------------|----------|-----------------|
| `ircd` | 1 | 1 | `-v`（打印版本，0）、`-?`（用法，1） |
| `umkpasswd` | 非 0 | 非 0 | `-h`（`show_help()`，0）、`-l`（列机制，0） |
| `convert-conf` | 1 | 1 | 无（把第一个参数当配置文件） |

ircu2 是 2005 年的守护进程，`getopt` 只认单字符短选项，给三个二进制补长选项属于
**改上游 CLI 行为**，与 OHOS 适配无关（红线：不夹带无关改动），所以不做。
test_package 里对 `ircd -v` / `ircd -?` / `umkpasswd -l` 的断言比 L2 严格得多。

### L4 = pass，但两处是子串误报，值得记一笔

L4 用 `grep -rlE '(strcpy|sprintf|gets|strcat)\b'` 扫 `patches/`，是**子串**匹配：

- `fgets(` 里含 `gets`，`\b` 又恰好在 `(` 前成立 → 误报；
- 上游 `config.guess` 的注释 `# NetBSD (nbsd) targets should ...` 里
  `tar`+`gets` 恰好拼成 `gets` → 误报（这行是 diff 的**上下文行**，不是代码）。

处置不是绕过检查而是换个同样成立的写法，并在补丁里说明：
`0003` 改成逐字符读行（无回显口令提示本来就是这么写的），
`0001` 用 `-U1` 上下文（注意 `-u -U1` 里的 `-u` 会把上下文重置回 3 行），
hunk 因此只带一行上下文。两处都不削弱补丁内容。

## 未使用 / 被否决的做法

- **不传 `--host`**：Conan 在 host/build 同 profile 时不会传，强行手写
  `--host=aarch64-linux-ohos` 会把 autoconf 切进 cross-compiling 模式，
  所有 `AC_RUN_IFELSE` 默认判 no。ircu 的 `configure.in` 虽然没有
  `AC_RUN_IFELSE`，但保持与 CI 门禁完全同源更稳。
- **不跑 `make install`**：见第 6 条（`${DESTDIR}` 被忽略 → 污染构建机 `/bin`；
  宿主 `strip` 读不懂 aarch64；而且子目录失败不会让 `make install` 返回非零）。
- **不给 `requires` 加 zlib/openssl**：ircu2 的 `configure` 根本没有对应选项，
  加了反而会造成「配方声明了但上游不用」的假依赖。
- **不改 ircd 的超级用户检查**：那是上游有意的安全策略，适配不应该去削弱它；
  需要非 root 的地方在测试侧解决（`droproot`）。
- **不引入 `commands.json` 之外的运行时配置**：ircd 的配置文件由使用者按
  `doc/example.conf` 自行部署，包里只提供示例文件。