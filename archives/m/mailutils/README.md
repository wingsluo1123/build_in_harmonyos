# GNU Mailutils 3.19 — HarmonyOS PC 适配

GNU Mailutils 是一套与协议无关的邮件框架：`libmailutils` 库族（邮箱/URL/
消息/MIME/Sieve/认证）、POSIX `mailx` 客户端及 `frm`/`from`/`readmsg`/`sieve`/
`mimeview`/`movemail` 等工具，以及 `imap4d`/`pop3d`/`comsatd`/`mda`/`lmtpd`
服务端。

本归档是上游 3.19 在 HarmonyOS PC（aarch64-linux-ohos）上的适配。Conan 包
类型为 library：安装 `libmailutils.so.9` 等 11 个共享库、`include/mailutils`
头文件，以及 `bin/` 客户端与 `sbin/` 服务端可执行文件（因此软件级目录提供
`commands.json`）。

上游地址：https://www.gnu.org/software/mailutils/

## 适配要点

- **config.guess / config.sub**：补 HarmonyOS 分支与 `linux-ohos` 内核项，
  configure 可正确得到三元组 `aarch64-unknown-linux-ohos`（不借助 `--build/--host`）。
- **autotools 临时目录**：HMDFS 把目录 owner 映射为固定 UID，`umask 077`
  创建的 `confXXXXXX`/`csXXXXXX` 目录对当前进程不可写，改为 `umask 022`。
- **OHOS libc 缺失接口**：`getspnam()`（shadow.h 存在但函数缺失）与
  `getutxent()`（utmpx.h 只有结构体、函数缺失）通过 configure 特性探针
  （`HAVE_GETSPNAM` / `HAVE_GETUTXENT`）按可用性选择代码路径，不使用平台宏。
- **文档再生成**：toybox `ls` 的 ISO-8601 日期击穿 automake 的 mdate-sh，
  触发 makeinfo（worker 无 texinfo）；将 `doc/texinfo` 的 stamp-vti 规则
  置为 no-op，保留发行包自带的 info/man。
- **dotlock**：HMDFS 不支持硬链接（`link(2)` 返回 EPERM），默认 dotlock 锁
  回退为 `O_EXCL` 直接创建锁文件，保证本地邮箱加锁可用。
- **Python 绑定**：OHOS `python3-config` 输出的 `-lintl` / `-lpython3.12`
  不在 Conan 依赖图中，使用 `--disable-python` 关闭（可选组件）。

## 依赖

无外部 Conan 依赖：核心框架使用自带的 gnulib，可选集成（GnuTLS/GSSAPI/
PAM/Guile/readline/fribidi/SQL/DBM）保持关闭。

## 测试

- 上游 `make check`（GNU Autotest）：1355 用例，1164 通过 / 163 失败 /
  28 跳过，失败全部来自构建沙箱限制（无 passwd 记录、HMDFS UID 映射），
  与库本身无关，详见 `3.19/reports/test-report.md`。
- 新增鸿蒙特有测试：`3.19/test_package/test_ohos_mailutils.sh`（平台身份、
  CLI/服务端冒烟、版本号）+ `test_mailutils.c`（消费者 API，含 dotlock 无硬
  链接路径验证）。

## 3.20 适配（主赛任务 #8661）

- 上游源码只取 GNU 官方 HTTPS 地址：`https://ftp.gnu.org/gnu/mailutils/mailutils-3.20.tar.xz`；SHA-256 为 `a8f3faab1edda5188bb5ca3e4e9c0c5bc72cd0dadf4e1f4799d27fa75c6ae829`。签名文件已下载，但设备与本机均无 `gpg`/`gpgv`，无法验证。
- 通过 HarmonyOS aarch64 的 Conan 配方构建 11 个共享库、客户端与服务器程序。3.20 配方显式声明 GnuTLS 3.8.10、libunistring 1.0、libtool 2.5.4，以运行上游 TLS/Unicode 测试并构建对应扩展；PAM、数据库、LDAP、Guile、readline、FriBidi 和 Python 集成保持关闭。
- 新增补丁处理 HarmonyOS triplet、HMDFS 临时目录权限与硬链接限制、OHOS libc 接口缺失、Texinfo 重生成问题，以及关闭 DBM 时 Sieve `uidnew` 的错误依赖。
- `testsuite/cwdrepl.c` 的测试辅助程序增加 `PWD`/`getcwd()` 错误处理；上游 `.at` 测试用例本身未改。
- 包装时保留链接器产生的 OHOS ELF 字节；真机没有 `patchelf`、签名器或 `llvm-objcopy`，Conan runenv 提供包内库目录。
- Mailutils 3.20 的真机 `make -j2 -k check` 与 test_package 真实测试结果见 `3.20/reports/test-report.md`。
