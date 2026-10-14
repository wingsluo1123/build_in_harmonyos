# physlock

用 PAM 认证的轻量级 Linux 控制台锁屏工具（等价于 `vlock -an`）：锁定全部虚拟终端，
只允许前台 VT 的会话用户或 root 解锁。

- 上游：Bert Muennich（`xyb3rt`），<https://github.com/xyb3rt/physlock>
  （原名 `muennich/physlock`，GitHub 301 重定向；仓库**已归档**，tag `v13` → commit `d4091fe3396f6c63e42ea165797062f6032779eb`）
- 许可证：GPL-2.0-or-later
- 语言 / 构建：C（5 个 `.c`）+ **手写 GNU Makefile**（非 autotools/cmake/meson）
- 产物：`bin/physlock`（单个可执行文件，setuid root）+ `share/man/man1/physlock.1`

## 用法（上游 README:52-62）

```sh
physlock              # 锁定全部 VT，用 PAM 认证前台会话用户 / root
physlock -d           # fork 并 detach（供 suspend/hibernate 脚本使用）
physlock -m           # 锁屏期间静音内核消息
physlock -p MSG       # 在口令提示前显示 MSG
physlock -h           # 打印 usage 并退出
physlock -v           # 打印版本并退出
```

> 真正锁定 VT 需要 root 权限与 `/dev/tty0`；`-h` / `-v` 为安全入口。

## OHOS 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | OHOS 无 `cc`/`gcc`（`cc: not found`），Makefile 的 `$(CC)` 默认 `cc` | 配方显式传 `CC=clang`（从 `tools.build:compiler_executables` 取） |
| 2 | 上游 `install` 目标硬编码 `install -m 4755 -o root -g root`，非 root/沙箱无法执行 | 配方只 `make`；`package()` 手工落 `bin/` 与渲染后的 `man1`（等价上游 install，零源码补丁） |
| 3 | OHOS lld 未默认 `--as-needed`，`-lsystemd` 被记为运行时 `DT_NEEDED` | 保持上游默认行为；`systemd/261` 作为 Conan requires 提供 libsystemd.so.0 |

`<utmp.h>` / `<paths.h>` / `<linux/vt.h>` 等由 OHOS musl libc 与内核头提供，源码零改动。

## 依赖

- `linux-pam/1.7.2`：`-lpam -lpam_misc`（`<security/pam_appl.h>`、`<security/pam_misc.h>`）
- `systemd/261`：`-lsystemd`（libsystemd 客户端库；`HAVE_SYSTEMD=1` 的链接线）

产物 `DT_NEEDED`：`libpam.so.0`、`libpam_misc.so.0`、`libsystemd.so.0`、`libc.so`。
注：`session.c` 的 sd-login 代码路径**未参与编译**（宏 `HAVE_SYSTEMD` 从未 `-D` 传入），二进制零 `sd_*` 符号。
详见 `physlock-13-deps/DEPENDENCY-REPORT.md`。

## 测试

上游**没有自动化测试**（无 `tests/`、Makefile 无 `check`/`test` 目标，见 `13/reports/upstream-test-entry.md`）。
`13/test_package/` 提供 9 例消费者验证（4 例鸿蒙特有：ELF 架构 / musl 解释器 / `.codesign` / 可执行性；
3 例 CLI 行为；2 例打包完整性），**不能替代上游测试统计**。
