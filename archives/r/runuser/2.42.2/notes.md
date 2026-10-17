# runuser 2.42.2 适配笔记

## 编译环境
- 构建系统: autotools（util-linux 源码树，仅启用 runuser 组件）
- 编译日期: 2026-10-15
- 编译器: clang/clang++ 15.0.4（aarch64-linux-ohos 目标）
- 状态: built

## 编译步骤

runuser 是 util-linux 2.42.2 的 login-utils 组件（login-utils/runuser.c，与 su 共享 su-common.c）。
从完整 util-linux 源码树中仅构建 runuser：

```bash
./configure --prefix=<prefix> --host=aarch64-linux-ohos --build=aarch64-linux-ohos \
  --disable-all-programs --enable-runuser \
  --without-systemd --without-selinux --without-audit \
  --disable-bash-completion --disable-nls --disable-plymouth-support \
  --without-cap-ng --without-utempter \
  --disable-makeinstall-chown --disable-makeinstall-setuid
make -j4 runuser
make install DESTDIR=<staging>
```

- configure 前注入 linux-pam/1.7.2 的 include/lib（CPPFLAGS/LDFLAGS），满足
  `UL_REQUIRES_HAVE([runuser], [security_pam_appl_h], ...)`。
- 运行冒烟：`runuser --help`、`runuser -V`（`runuser from util-linux 2.42.2`）均通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 OHOS | config.guess 无 HarmonyOS 检测分支 | 补 `*:HarmonyOS:*:*` 分支输出 `aarch64-unknown-linux-ohos`（0001 补丁） |
| 2 | configure 报 "runuser selected, but required GNU utmpx functions not available" | OHOS musl 无 GNU utmpx 扩展（updwtmpx 等） | 放宽 runuser 的 gnu_utmpx 检查为直接通过（0002 补丁，参考 util-linux-login 0003） |
| 3 | config.status 报 "cannot create ./confXXXXXX/subs1.awk: Permission denied"（E011） | configure 用 umask 077 建临时目录，OHOS HMDFS 上 0700 目录被强制降权不可写 | configure 中 umask 077→022（0002 补丁） |
| 4 | lib/shells.c 编译报 getusershell 家族未声明（-Wint-conversion 硬错） | OHOS musl 无 getusershell(3) 声明/实现 | shells.h 补声明 + shells.c 补 no-op stub（0003/0004 补丁，参考 util-linux-login 0004） |
| 5 | 链接报 undefined symbol: updwtmpx | su-common.c log_btmp 调用 updwtmpx，OHOS musl 无此函数 | HAVE_UPDWTMPX 守卫（0005 补丁，参考 util-linux-login 0002） |

## 源码修改

5 个补丁（patches/0001-0005）：
- 0001-config-config.guess.patch：config.guess 增加 HarmonyOS 检测
- 0002-configure.patch：放宽 runuser gnu_utmpx 检查 + umask 077→022
- 0003-include-shells.h.patch：非 glibc 下声明 getusershell 家族
- 0004-lib-shells.c.patch：非 glibc 下提供 getusershell 家族 no-op stub
- 0005-login-utils-su-common.c.patch：HAVE_UPDWTMPX 守卫 updwtmpx 调用

## 依赖版本

- linux-pam/1.7.2（runuser 需 PAM header 与 libpam，制品仓已发布，配方 `self.requires("linux-pam/1.7.2")`）

## 验证结果

```bash
# W3 本地 CI 模拟（finish 内置）
setup.sh                    → 通过
build_and_test.sh runuser   → 通过（conan create + L0-L5），.ci-result.json exit_code=0

# 上游测试（R51 清点+运行，详见 reports/test-report.md）
bash tests/run.sh login/islocal     → PASS
bash tests/run.sh login/logindefs   → PASS
# util-linux 2.42.2 注册 91 组/372 个测试脚本；runuser 无专属功能测试；
# 其余 370 个脚本针对 --disable-all-programs 未启用的其他程序，不具备运行条件，未申报为通过。

# 自研 test_package 测试（test.c，4 项断言）
runuser 二进制存在可执行 + --version/--help 退出码 0 → 全部通过
```

## 交付物

无独立打包产物（runuser 为单一 CLI 二进制，经 conan create 打包为 runuser/2.42.2@ohpcd/stable）。

## 注意事项

- util-linux 测试脚本 shebang 为 `#!/bin/bash`，OHOS 无 `/bin/bash`，本地运行测试时改用
  `/storage/Users/currentUser/usr/local/bin/bash`；toybox xargs 不支持 `-I`，需注入 GNU findutils xargs。
  这些仅本地测试环境调整，未进入配方补丁（CI 为 Linux 环境，无需该调整）。
- 与 util-linux-login/2.42.2 同源码同版本，5 个适配点中 4 个与其补丁同源（config.guess/utmpx/umask/getusershell）。
