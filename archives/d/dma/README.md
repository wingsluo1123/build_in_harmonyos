# dma

## 简介

dma（DragonFly Mail Agent）是一个极简 MTA：把邮件**本地投递**到 `/var/mail`，
并可把外发邮件经**明文 SMTP 或 SSL/TLS relay** 投递到上游 smart host，在小规模
机器上充当 `sendmail(8)` 的替代。它是 DragonFly BSD 的官方 MTA，源码同时被
FreeBSD 收录。

- 官网 / 源码: https://github.com/corecode/dma
- 许可证: BSD-3-Clause
- 构建系统: 裸 BSD 风格 `Makefile`（**非** autotools —— 无 `configure`/`Makefile.am`/
  `CMakeLists.txt`/`meson.build`，逐项在场检查已核实）

## 产物

| 路径 | 说明 |
|---|---|
| `bin/dma` | MTA 主程序（sendmail 替代，`mailq`/`newaliases` 语义由 `argv[0]` 分派） |
| `lib/dma-mbox-create` | root 建 mailbox 用的辅助工具（上游以 `-m 4754` 安装） |
| `share/man/man8/dma.8` | man 手册 |
| `etc/dma/{dma.conf,auth.conf}` | 配置模板（装进包内，**不触碰** `/etc`） |

## OHOS 适配

- **依赖**：`openssl/1.1.1w`（`requires`）、`bison/3.8.2` + `flex/2.6.4`（`tool_requires`）——
  三者在制品仓均已发布（`preflight_check.sh` 实测 rc=0）。
  选 1.1.1w 因为 `crypto.c:126` 的 `#if (OPENSSL_VERSION_NUMBER >= 0x10100000L)`
  分支取 `TLS_client_method()`，1.1.1w 正中该分支；仓内同族 sendmail 模拟器
  `ssmtp/2.64` 亦用同一版本。
- **`LDADD` 命令行覆盖**：上游 `Makefile:18` 默认 `-lssl -lcrypto -lresolv`，
  musl/OHOS 内置 resolver ⇒ 覆盖为 `-lssl -lcrypto` 去掉 `-lresolv`
  （命令行变量优先级高于上游 `LDADD?=`，**不修改上游文件**）。
- **`CFLAGS` 不覆盖**：Makefile 向其追加 `-DDMA_VERSION`/`-DLIBEXEC_PATH`/`-DCONF_PATH`，
  覆盖会触发 `dma.h:76 #error Please define CONF_PATH` ⇒ OpenSSL 头改走 `CPPFLAGS`。
- **`package()` 手工安装**：上游 `install` 目标在 OHOS 有四重墙（`Makefile:53-54`）——
  `install` 命令不在 PATH（rc=127）、`-o root` 而运行 uid 为 20020084、
  `-g mail` 组不存在（`KeyError`）、`-m 4754`/`-m 2755` 的 setuid/setgid 位被
  文件系统剥离（`chmod u+s` 返回 ok 而 `stat` 报 `setuid=False`、mode 实得 `0o770`）。
  故配方用 `self.copy` + `os.chmod(0o755)` 自装，属 `适配检查清单` Makefile §3 的文档化做法。
- **运行期能力面**：`dma.c:464` 仅在 root 下才走 `setuid` 降权（`dma.c:476`），非 root 整块跳过；
  `/var` 目录不存在（ENOENT）、`/etc` 只读（EROFS）⇒ 上游 `DMASPOOL=${VAR}/spool/dma`
  无处安放。**核心投递路径不纳入测试断言**，披露见 `0.14/notes.md`。

## 功能验证

上游**没有测试套件**（顶层 `Makefile` 无 `check`/`test` 目标；`test/` 仅含数据文件
`quote.rfc2822`；全仓无 `make check`/`ctest`/`pytest`）。消费者验证走 `test_package`
两条**参数期**断言（均早于 `dma.c:606 parse_conf`，不读配置、不碰 spool、不碰投递）：

```bash
dma -Z        # 未知选项 → stderr `invalid argument: `-Z'`、退出码非 0      (dma.c:581-582)
dma -bp -q    # 队列模式互斥被拒 → stderr `sending mail and queue operations
              #   are mutually exclusive`、退出码非 0                        (dma.c:585→588-590)
```

> 断言 2 的真实触发链：`-bp` → `showq=1`（`dma.c:513-515`）、`-q` → `doqueue=1`；
> `-q` 后无操作数时 musl 的 getopt 缺参分支把 `optind` 推到 `argc+1`，`dma.c:585
> argc -= optind` 得 `-1 ≠ 0` ⇒ 先触发 `dma.c:588` 的操作数护栏（`dma.c:590`）。
> `dma.c:592-593`（`conflicting queue operations`）需要 `-q` 真吃到一个参数
> （如 `dma -bp -q x`）才会命中，不是本断言的命令。

> `-h`/`-V`/`--help` **不能用作断言**：`dma.c:503` 的 getopt 串里 `h/U/V/v/X` 全部落在
> "Ignored options" 段纯 `break`（不打印、不退出），全程序无 usage 输出路径，也不支持长选项。

## 参考

- 上游: https://github.com/corecode/dma
- man page: https://man.freebsd.org/cgi/man.cgi?query=dma
