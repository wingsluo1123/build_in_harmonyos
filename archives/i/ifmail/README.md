# ifmail (ifmail-tx)

`ifmail` 是 FidoNet 与 Internet 之间的传输与网关套件：`ifcico` 通过串口或
TCP/IP 跑 FTN 会话（FTSC-0001、EMSI、YooHoo、Wazoo、Hydra、Janus、Zmodem、
Xmodem、binkp），`ifgate` 一族在 FTN netmail/echomail 与 RFC-822 邮件、
RFC-1036 新闻之间双向网关，另有节点表（nodelist）索引与查询工具。
上游 <http://ifmail.sourceforge.net/>（原 www.average.org/ifmail 已改为跳转页），
本仓引入的是 tx 分支最后一个版本 2.14tx8.10（1999-04-02）。

- 版本目录：`2.14tx8.10/`（配方、15 个补丁、上游自测夹具、消费者测试、鸿蒙特有测试、报告）
- 交付物：`bin/` 下 14 个可执行文件
  - ifcico 侧：`ifcico` `ifindex` `ifinfo` `ifreq` `ifroute` `nlpatch` `nlookup`
  - ifgate 侧：`ifmail` `ifnews`（上游为 ifmail 的硬链接）`iftoss` `ifpack` `ifunpack` `ifstat`
  - iflib 侧：`make_new_ref`
- 数据与文档：`share/ifmail/maptabs/`（字符集转换表，即编译期 MAPTABDIR）、
  `etc/ifmail/{config,Areas}.sample`、`share/man/man8|man3|fr/man8`、`share/doc/ifmail/`
- 依赖：运行期无（gdbm/1.23 静态链入）；构建期 gdbm/1.23（提供 ndbm 兼容层）
  与 bison/flex/awk（生成 parsedate.c、flagexp.c、flaglex.c、ftscprod.c）

## 功能概述

- FTN 邮件传输：拨号（modem chat、termios）与 TCP（binkp、telnet 风格）两种承载
- 网关：`ifmail`（mail→FTN）、`ifnews`（news→FTN，同一二进制的硬链接）、
  `iftoss`（把 inbound 的 packet 投入 echomail）、`ifpack`/`ifunpack`（打包/解包）
- 节点表：`ifindex` 建 ndbm 索引，`nlookup`/`ifinfo` 查询，`ifroute` 选路与 MX 查询，
  `nlpatch` 增量更新
- 字符集转换：`misc/maptabs` 下的双向转换表（cp437/cp850/cp866/koi8/iso-8859-* 等）
- MSGID <-> Message-ID 参考库（REFERENCES_MSC96，走 ndbm）

## OHOS 适配

要点见软件级 `manifest.yaml` 的 `ohos_adaptation` 与版本级 `2.14tx8.10/notes.md`。
与 Linux/glibc 的主要差异：

1. **没有 ndbm**：musl 不提供 ndbm/dbm，改由 gdbm 的 compat 层承载（制品仓
   gdbm/1.23 是 `--enable-libgdbm-compat` 的那个版本；gdbm/1.24 关掉了 compat，
   连 `<ndbm.h>` 都没有）。gdbm 的 compat 头**没有 include guard**，消费方必须
   保证同一 TU 只包含一次。
2. **musl 的 resolver 是精简版**：只有类型 `struct __res_state`（源码注释自称
   "unused; purely for broken apps"），没有 `_res` 对象，也没有 libresolv 私有的
   `_getshort`/`_getlong`，且不存在 `libresolv`（resolver 在 libc 内）。
3. **没有 BSD 正则**：`re_comp`/`re_exec` 只有 glibc 在 `_REGEX_RE_COMP` 下提供，
   musl 只有 POSIX `regcomp`/`regexec`。
4. **clang 15 拒绝 K&R varargs**：`<varargs.h>` 是 `#error` 桩，`va_dcl`/
   `va_start(args)` 必须转 C99 `<stdarg.h>`。
5. **`<linux/signal.h>` 内核头与 musl 用户态头冲突**：`sigset_t`/`sigaltstack`/
   `sigval` 重复定义；musl 自己在 `<signal.h>` 提供 `struct sigcontext`。
6. **`-fno-common`**：重复的暂定定义（tentative definition）从"能链接"变成硬错误。
7. **/tmp 只读、无 /bin/sh**：调试/日志/伪 spool 等编译期路径统一指到
   package_folder，make 的 `SHELL` 指向 `CONFIG_SHELL`。

已知限制：

- `USE_NLS=no`：不构建 po/ 下的消息 catalog（需 msgfmt + libintl），只影响交互
  消息的本地化，核心功能不受影响。
- `make_new_ref` 使用编译期常量 `REF_DBM=/var/spool/ifmail/refdb`（上游 main(void)
  不读配置文件），系统上没有该路径时按上游行为 `exit(2)`。
- 站点配置需用 `-I <file>` 指定；`etc/ifmail/config.sample` 是上游原始示例，
  其 spool 路径与 `include /etc/ifmail/passwds` 在新系统上不存在。

## 参考资料

- 上游主页：<http://ifmail.sourceforge.net/>
- 源码 tarball（唯一存世的原版 release，非 Debian 重打包）：
  <https://deb.debian.org/debian/pool/main/i/ifmail/ifmail_2.14tx8.10.orig.tar.gz>
- Debian 打包（quilt 系列未使用）：<https://salsa.debian.org/md/ifmail>
- 协议文档：tarball 内 `ifcico/fta-1005.txt`、`ifcico/ftscprod.090`、`ifcico/hydra.LICENSE.DOC`
