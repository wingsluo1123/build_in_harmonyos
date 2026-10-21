# esmtp 1.2 适配笔记

## 编译环境
- 构建系统: autotools（configure/Makefile.in 随 tarball 预生成，无需 autoreconf）
- 编译日期: 2026-10-08
- 编译器: clang 15（OHOS aarch64，ci/conan/profiles/ohos-aarch64）
- 状态: built
- 配方目录: archives/e/esmtp/1.2；软件级 commands.json 已声明（CLI 包，R38）

## 编译步骤

1. `bash ci/scripts/preflight_check.sh esmtp/1.2` — 首跑时 conanfile 未生成，报「未找到依赖声明」并 RC=0；配方就位后复跑，精确依赖 `libesmtp/1.1.0` 在 ohpcd 已发布（recipe + OHOS/armv8 二进制均在，`conan list "libesmtp/1.1.0:*" -r ohpcd` 实测 `os: OHOS / arch: armv8 / shared: True`）。
2. `ohc-run.py recipe-search esmtp` — 语料 8264 条无相似配方，首稿手写。
3. `ohc-run.py init-build esmtp 1.2 --url=<SourceForge 官方直链>` — 下载 127921B 并解包（41 条目）。
4. 配方：`conanfile.py`（autotools）+ `conandata.yml` + `patches/0001` + `test_package/`。
5. `conan create … -pr:h/-pr:b=ohos-aarch64 --build=missing` → `make -j1` → `make check` → `make install DESTDIR=<package>`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SourceForge 直链取源反复 403 / 404 | ① 路径少写一段：真实路径是 `project/esmtp/esmtp/1.2/`（两段写法实测 404，body「resource could not be found」）；② 带浏览器 UA 时 Cloudflare 挑战页返回 403（`Just a moment…` 或 2 字节 plain），换成 curl 默认 UA 即 302→master.dl→200 | 按实测取端点：`https://downloads.sourceforge.net/project/esmtp/esmtp/1.2/esmtp-1.2.tar.bz2`，默认 UA 跟随 302，200/127921B/md5 `79a9c1f9023d53f35bb82bf446150a72`（与 SF 官方 API 记录一致）。**403（UA 触发的挑战）、404（路径错）、000（超时/DNS 失败）三类分开记，不合并成「不可达」** |
| 2 | `configure: libESMTP library not found` | 上游 `configure.ac` 无条件执行 `libesmtp-config --version`；libESMTP ≥ 1.0 改 meson 后只装头文件/so/pc，不装该脚本 | 配方 `generate()` 生成中性 `libesmtp-config` helper（仅回显 conan 依赖的 include/lib 目录）并 prepend 到 PATH；不注入任何平台宏 |
| 3 | 安装出的 `bin/sendmail` 等符号链接悬空 | 上游 `install-exec-hook` 写 `$(LN_S) $(bindir)/esmtp`（绝对路径），而 conan 用 `--prefix=/` + `DESTDIR=<package>`，链接目标 `/bin/esmtp` 落在包外 | `package()` 内把「绝对目标且在包内确有对应文件」的链接改写为相对路径，其余不动 |
| 4 | `config.status` 报 `./confXXXXXX/subs1.awk: Permission denied`（G2 第一轮红） | `configure:5192/5197` 用 `umask 077 && mktemp -d ./confXXXXXX` 建临时目录，在本文件系统上得到 `drwx--S---`，随后写 `$tmp/subs1.awk` 被拒 | E011/E114 受控方案：`source()` 里 `replace_in_file(configure, "umask 077", "umask 022")`（保留真实临时目录创建，不换环境、不伪造成功）。出处 `经验库/14-最终防错清单.md:114`、`手册/07 §12.1` |
| 5 | 真实投递一律 `Bad system call (core dumped)`，exit **159**（G2 第二轮红） | `main.c:34 drop_sgids()` 无条件 `setregid(real_gid,real_gid)`；本平台不实现 `setregid`/`setreuid`，seccomp 直接 **SIGSYS(31)**（fork-per-syscall 探针实测，见「能力墙」小节）。而本包 uid==euid、gid==egid（20020084/20020084），该调用本就是空操作 | `patches/0002-skip-noop-setregid.patch`：加 `real_gid != effective_gid &&` 守卫 —— 有 setgid 才真降权，无 setgid 时跳过空操作；语义不变，不含 `__OHOS__` |
| 6 | `--version`/`--help` 非 0（L2 冒烟） | esmtp 1.2（2009）只有 sendmail 短选项，长选项落进 `default:` → `exit(EX_USAGE)` | `patches/0001-add-informational-long-options.patch` |

| 7 | 装出来的二进制在 `conanrun` 之外跑不起来 | 链接的是 conan 缓存里的共享库 `libesmtp.so.6`，无 rpath | `AutotoolsToolchain.extra_ldflags` 追加 `-Wl,-rpath,<依赖 libdir>`；configure 的 conftest 另由 buildenv 的 `LD_LIBRARY_PATH` 兜底 |


## 源码修改

- `patches/0001-add-informational-long-options.patch`（patch_type: portability）
  `main.c`：在 getopt 循环前加 `--version`（打印 `PACKAGE_STRING`）与 `--help`（打印 usage）两个分支，均 `exit(EX_OK)`。不含 `__OHOS__`、不含任何平台条件编译（PF5 合规）。

## 依赖版本

- `libesmtp/1.1.0`（ohpcd 已发布；其自身 requires `openssl/3.5.6#748fc4de…`）
- 构建工具：系统 flex/bison（`/data/service/hnp/bin`）仅在 `.l/.y` 比 `.c` 新时才会被用到，tarball 内 `lexer.c`/`parser.c` 已预生成

## 验证结果

```bash
# W0 精确依赖（配方就位后复跑 preflight）
bash ci/scripts/preflight_check.sh esmtp/1.2        # 预检通过（无未发布依赖）
conan list "libesmtp/1.1.0:*" -r ohpcd              # OHOS/armv8 二进制在

# 上游测试资产清点（结论：零）
grep -cE 'TESTS|check_PROGRAMS' esmtp-1.2/Makefile.am   # 0
find esmtp-1.2 -type d -name 'test*' -o -name tests -o -name check -o -name spec   # 0
# 八类跨框架标记（Test::More/use_ok/def test_/TEST_CASE/add_test/enable_testing/gtest/TAP）全文 0 命中

# 端到端（test_package/test.sh，回环非特权端口起本地 ESMTP 监听）
esmtp --version                       # esmtp 1.2
esmtp -C esmtprc -f sender@example.com rcpt@example.com < msg   # rc=0，transcript 见 EHLO/MAIL FROM/RCPT TO/DATA/QUIT
```

## 注意事项

- **能力墙实测（本包判甲，读数全列，供主理独立复核）**：
  - ① 非特权端口回环 TCP：`bind 127.0.0.1:<随机高端口>` + `connect` + 收 banner **OK**（29ms，实测端口 45741）。
  - ② `bind :25` → `EACCES(13)`；`socket(AF_INET, SOCK_RAW, IPPROTO_ICMP)` → `EACCES(13)`（**进程权限**，esmtp 两者都用不到 —— 它是普通 TCP 客户端）。
  - ③ **fork-per-syscall 探针**（30 行级、不含第三方代码，`~/tmp/uc2/esmtp/probe/forkprobe.c`）：`setregid` → **SIG31 Bad system call**、`setreuid` → **SIG31**；`setgid`/`setuid`/`setresgid`/`setresuid`/`setgroups`/`initgroups`/`chown`/`connect-loopback` **全部正常返回**（exit 77 = 探针自测通过位）。`/proc/self/status`：`Seccomp: 2`、`Seccomp_filters: 1`。⇒ 被拦的**只有 setregid/setreuid 两个号**，与 `E051` 记载一致；esmtp 的 `drop_sgids()` 恰好无条件调 `setregid`，且本包 uid==euid、gid==egid（20020084/20020084），该调用是**空操作** ⇒ 用 `0002` 等值守卫跳过，语义不变。
  - ④ 外发：`1.1.1.1:25/587/465` 与 `:443` **Timeout 6002ms**（000，设备无可用外网 SMTP 面）；`1.1.1.1:80` 61ms、`208.67.222.222:53` 43ms 连通。
  - ⑤ 判甲依据：**协议面可在回环非特权端口完整复现**（test_package 实测 EHLO→MAIL FROM→RCPT TO→DATA→QUIT 全绿），被拦的两个 syscall 与 SMTP 功能无关且属空操作；**外发端口超时如实披露、不入任何断言**。若主理判乙，本链停在此处，不建 PR。
- **DNS**：`sourceforge.net` 主域 3 次 `getaddrinfo` 均 `EAI_AGAIN`（解析失败），`downloads.sourceforge.net` → 104.18.12.149 正常；子域可用、主域不可用，与 `ebook-tools` 同款。
- 其余失败形态（与 403/404 分开记）：`versaweb/kumisystems/newcontinental/liquidtelecom/ayera/sentence/ufpr/nchc/onix/cfb/altushost.dl.sourceforge.net` = DNS 解析失败（curl rc=6）；`iweb/cytranet.dl` = 连接超时（rc=28，http 000）；`freefr.dl` = 证书过期（rc=60）；`archive.org/web.archive.org` = DNS 失败；`fossies.org` = 401；`ftp.osuosl.org/pub/blfs/conglomeration/esmtp/` = 404。
- 次级可用源（同字节）：`https://cdn.netbsd.org/pub/pkgsrc/distfiles/esmtp-1.2.tar.bz2` 实测 200/127921B/md5 一致；Debian 池 `deb.debian.org/debian/pool/main/e/esmtp/esmtp_1.2.orig.tar.bz2` 同样 200/127921B/md5 一致（**仅作交叉印证，不作配方货源** —— PF7 拦 Debian 重打包源）。
- 设备 `/tmp` 只读，test_package 临时目录落 `$TMPDIR`（默认 `$HOME/tmp`）。
- `package_type=application`，软件级 `commands.json` 必须与 `esmtp/1.2` 对齐（R38/L0k）。
---

**编译结束**: 2026-10-08 21:27
**最终状态**: built
