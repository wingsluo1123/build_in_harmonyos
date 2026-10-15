# mailx 8.1.2_git20220412 适配笔记

## 编译环境
- 构建系统: makefile（上游 OpenBSD bsd.prog.mk，适配改写为 GNU make 兼容）
- 编译日期: 2026-10-14
- 编译器: clang（aarch64-linux-ohos 交叉编译，由 HMBS 注入 tools.build:compiler_executables）
- 状态: built（配方与已合入的 bsd-mailx 8.1.2-0.20220412cvs 同源，待 HMBS 真机预检确认）

## 上游说明

mailx 8.1.2_git20220412 是 Alpine 对 BSD mailx 快照 20220412 的命名，
与 Debian 的 bsd-mailx 8.1.2-0.20220412cvs 为同一上游源码（Debian 官方
GitLab salsa.debian.org 托管，归档 sha256 相同）。仓内已合入
`archives/b/bsd-mailx/8.1.2-0.20220412cvs`（PR !8719），本配方复用其全部
适配结论，仅安装二进制命名改为 `mailx`（与 Alpine 包名一致）。

## 编译步骤

```bash
# 源码获取（salsa.debian.org 官方托管仓库）
# https://salsa.debian.org/debian/bsd-mailx/-/archive/debian/8.1.2-0.20220412cvs-1.1/bsd-mailx-debian-8.1.2-0.20220412cvs-1.1.tar.gz

# 构建（无 configure，直接 make；CC 由 conan tools.build:compiler_executables 注入）
make -j1 CC="clang"

# 安装（标准布局 BINDIR=bin）
make install DESTDIR=$PACKAGE_FOLDER
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | bsd.prog.mk 无法在 OHOS 构建 | 上游 Makefile 是 OpenBSD 专用（`.include <bsd.prog.mk>`），GNU make 不识别 | 改写为 GNU make 兼容 Makefile（patch 0001），安装名为 mailx |
| 2 | `vis.h` 不存在 | OHOS libc 无 BSD vis(3) API（strvis/strnvis） | 移植 OpenBSD 官方 vis.c/vis.h，经 conanfile exports_sources 随配方打包（不引入 libbsd 依赖） |
| 3 | `__va_list` 未定义 | OpenBSD 特有类型，OHOS 无 | 改为标准 `va_list`（patch 0003） |
| 4 | `pledge()` 不存在 | OpenBSD 特有 syscall | 删除调用（同 Debian 31 patch）（patch 0006） |
| 5 | `user_from_uid`/`uid_from_user` 未定义 | BSD libutil 特有函数 | 改用 POSIX `getpwuid`/`getpwnam`（patch 0013） |
| 6 | `warnc()` 未定义 | BSD err.h 特有（带 errno 参数的 warn） | 提供兼容实现（patch 0005） |
| 7 | `GLOB_BRACE`/`ALTWERASE`/`CCEQ`/`_PATH_CSHELL` 未定义 | OHOS libc 缺失 BSD/GNU 扩展 | `#ifndef` 兼容守卫（patch 0004/0008/0011） |
| 8 | `OPEN_MAX` 未定义 | OHOS 无此宏 | 改用 `FOPEN_MAX`（同 Debian 27 patch）（patch 0012） |
| 9 | `/tmp` 只读 | OHOS 设备 /tmp 只读，mailx 固定用 /tmp 作临时目录 | 适配遵循 `$TMPDIR` 环境变量（同 Debian 36 patch）（patch 0010，HMBS 注入任务独立 TMPDIR） |
| 10 | OHOS `install` 命令不支持 `-p -c` 选项、不支持多源安装 | 精简 install 调用 | Makefile install 改为单文件 `install -m MODE`（patch 0001） |
| 11 | `LOCK_EX` 未定义 | quit.c 缺 `sys/file.h` | 补头文件（patch 0009） |
| 12 | `ctime` 隐式 int | names.c/util.c 缺 `time.h` | 补头文件（patch 0007/0012） |

以上结论全部来自已合入的 bsd-mailx 适配实证（同源归档，同补丁集）。

## 源码修改

15 个补丁（13 个跟踪文件补丁 + 2 个新增 vis 文件走 exports_sources）：
- patches/0001-Makefile.patch — GNU make 兼容 + 标准 BINDIR 布局 + install 兼容（安装名 mailx/mailx.1/share/mailx）
- patches/0002-def.h.patch — vis.h 本地引用 + stdarg.h
- patches/0003-extern.h.patch — __va_list → va_list
- patches/0004-fio.c.patch — GLOB_BRACE 兼容
- patches/0005-lex.c.patch — warnc 兼容实现
- patches/0006-main.c.patch — 删除 pledge
- patches/0007-names.c.patch — 补 time.h
- patches/0008-pathnames.h.patch — _PATH_CSHELL 回退
- patches/0009-quit.c.patch — 补 sys/file.h
- patches/0010-temp.c.patch — $TMPDIR 支持
- patches/0011-tty.c.patch — ALTWERASE/CCEQ 兼容
- patches/0012-util.c.patch — OPEN_MAX→FOPEN_MAX + time.h
- patches/0013-v7.local.c.patch — user_from_uid→getpwuid
- vis.c/vis.h（新增文件，OpenBSD 官方源移植，exports_sources 打包）

## 依赖版本

零外部依赖（无 requires）。不引入 liblockfile/libbsd：
- liblockfile 是 Debian 特有安全修复（setgid 方案），非上游硬依赖
- libbsd 仅为 strlcpy/strvis 提供，OHOS musl 已含 strlcpy/strlcat，vis 用移植实现替代

## 验证结果

上游无测试用例（穷尽核查见 test_package/MANIFEST.yml 审计：OpenBSD bsd.prog.mk
仅有 all/clean/install/distribution 目标，无 check/test 目标，无 tests/ 目录）。
test_package 以自研功能测试集补全覆盖（4 组 9 断言），测试输出打印
HMBS_TEST_PACKAGE_RESULT / HMBS_UPSTREAM_TEST_RESULT 机器证据标记。
真机预检结论待 HMBS 回填（本轮仅提交未验证工作树，不创建 PR）。

```bash
# 真机功能验证（待 HMBS 预检执行）
python3 test_package/test_mailx.py <package>/bin/mailx
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/mailx | 主程序（mailx 命令行邮件客户端） |
| share/man/man1/mailx.1 | man 手册 |
| etc/mail.rc | 全局配置文件 |
| share/mailx/mail.help, mail.tildehelp | 帮助文件 |

## 注意事项

- 发送邮件依赖外部 sendmail（`/usr/sbin/sendmail`），OHOS 默认无此命令；`-f` 读取 mailbox、交互命令等核心功能完整可用
- 上游无测试用例，test_package 以自研功能测试集补全覆盖（4 组 9 断言）
