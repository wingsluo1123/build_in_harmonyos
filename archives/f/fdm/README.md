# fdm 2.2 — HarmonyOS 编译记录

## 概述

fdm（https://github.com/nicm/fdm）是 Nicholas Marriott 写的终端邮件过滤/读取器：
从 POP3 / POP3S / IMAP / IMAPS / NNTP / maildir / mbox / stdin 取信，用
`match … action …` 规则树过滤，再投递到 maildir / mbox / pipe / stdout / write /
SMTP / LMTP / IMAP 等目标；取信缓存落在 TDB。

**编译状态**: ✅ 成功（built）

## 编译环境

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS HongMeng Kernel aarch64 |
| 编译器 | clang 15（SDK /data/service/hnp） |
| C 库 | musl libc |
| 依赖 | tdb/1.4.15、zlib/1.3.1.1、openssl/3.5.6、pcre2/10.48 |
| 构建工具 | automake/1.18 + libtool/2.5.4 + bison/3.8.2（conan tool_requires）；autoconf/m4 用 SDK 自带 |

## 编译步骤

```bash
mkdir -p etc && autoreconf -fi          # tag 归档无 configure，自举
sed -i 's/umask 077/umask 022/g' configure   # E011，必须在 autoreconf 之后
./configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-ohos --enable-pcre2
make && make check && make install DESTDIR=<staging>
```

产物：`bin/fdm`、`share/man/man1/fdm.1`、`share/man/man5/fdm.conf.5`。

## 补丁说明

**无源码补丁**（patches/ 为空）：三处适配分别由自举步骤、configure 命令行参数、
上游自带的 PCRE2 后端解决，未修改任何上游源文件。

## 已知问题 / 平台限制

- **运行期需要 passwd 条目**：fdm 启动时 `getpwuid(getuid())` 失败即
  `log_warnx("unknown user: %lu")` + `exit(1)`（fdm.c:433-436）。OHOS 应用 uid
  （本机 20020084）不在 `/etc/passwd`（389 行，root/系统服务账号）内，因此
  fdm 在本平台只能跑到「加载 + 启动期初始化」这一步；消费者测试据此设计断言。
- **锁文件**：非 root 时锁文件写 `$HOME/.fdm.lock`，HOME 可写即可；`/var`、`/etc`
  在 OHOS 上只读，但 fdm 只把它们编进默认路径（`-DSYSCONFFILE`/`-DSYSLOCKFILE`），
  安装阶段不写入。
- 上游 `configure` 把 `-I/usr/local/include`、`-L/usr/local/lib` 追加在
  CPPFLAGS/LDFLAGS 末尾；conan 依赖路径排在其前，链接优先命中依赖包。

## 验证结果

- `conan create`（干净源码、CI 同源路径）通过：configure 全绿（tdb/zlib/crypto/ssl/
  pcre2 探测命中），74 个 C 源文件 + bison 生成的 parse.c + lex.c 编译通过，链接成
  `fdm` ELF（5.6 MB，`/lib/ld-musl-aarch64.so.1`）。
- `make check`：上游 Makefile.am 无 `TESTS`/`check_PROGRAMS`、无 tests/ 目录
  ⇒ `Nothing to be done for 'check-am'`（上游 N=0）。
- 消费者测试（test_package/test.sh）在真机实跑 3 组断言：usage 参数面、启动期
  动态链接（无 loader 报错）、依赖库在 conanrun 环境下可解析。
