# physlock 13 适配笔记

## 编译环境
- 构建系统: **makefile**（上游手写 GNU Makefile，非 autotools/cmake/meson）
- 编译日期: 2026-10-13
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang`，OHOS aarch64 工具链）
- 目标平台: os=OHOS / arch=armv8（triplet `aarch64-linux-ohos`）
- 状态: built

## 上游核验
- 上游仓库：<https://github.com/xyb3rt/physlock>（原名 `muennich/physlock`，GitHub 301 重定向；仓库已归档）
- tag `v13` → commit `d4091fe3396f6c63e42ea165797062f6032779eb`（归档时间 2019-01-29）
- 官方源码：`https://github.com/xyb3rt/physlock/archive/refs/tags/v13.tar.gz`
  - sha256 `9ae4716a1e916f141e47a01b439133ca382281ebdcbec1e53f85da6771774bd6`（14123 字节）
  - 与 Debian canonical 源 `physlock_13.orig.tar.gz`（sha256 `a1203050…c1ba`）解包后内容**逐字节一致**（仅 tar/gzip 封装不同）

## 编译步骤

```bash
# 依赖（并入 Conan 配方 requirements）
#   linux-pam/1.7.2 -> -lpam -lpam_misc
#   systemd/261     -> -lsystemd（libsystemd 客户端库）
make CC=clang \
     CFLAGS="-fPIC -O2" \
     CPPFLAGS="-I<linux-pam>/include -I<systemd>/include" \
     LDFLAGS="-L<linux-pam>/lib -L<systemd>/lib" \
     -j1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make` 报 `cc: not found`（若直接裸跑） | OHOS 无 `cc`/`gcc`，而 Makefile 的 `$(CC)` 默认 `cc` | 显式传 `CC=clang`（配方从 `tools.build:compiler_executables` 读取，R33） |
| 2 | `make install` 报权限错误 | 上游 install 目标硬编码 `install -m 4755 -o root -g root`，非 root 环境无法 chown（README 亦注明 install 需 root） | 配方不调用 `make install`；`package()` 手工落 `bin/physlock` + 渲染 `share/man/man1/physlock.1`（等价结果，零源码改动） |
| 3 | `DT_NEEDED` 出现 `libsystemd.so.0`（未使用任何 `sd_*` 符号） | OHOS lld **未默认 `--as-needed`**，链接行的 `-lsystemd` 被记录为运行时依赖（Debian gcc 默认 `--as-needed`，其二进制无此项） | 保持上游默认行为（不加 `--as-needed`）；`systemd/261` 作为 Conan requires，消费者经 Conan 环境可解析 libsystemd.so.0 |

> 说明：`Makefile` 的 `HAVE_SYSTEMD` 是 **make 变量**，从未以 `-DHAVE_SYSTEMD` 传入编译器 →
> `session.c` 的 `#if HAVE_SYSTEMD` 恒为假，编译 `#else` stub（`get_user_systemd()` 直接 `return -1`），
> 二进制零 `sd_*` 符号。`-lsystemd` 仅出现在链接行（要求 `libsystemd.so` 存在）。

## 源码修改

**无。** 上游 v13 源码零改动（无 `patches/`）。

## 依赖版本

| 依赖 | 版本 | 类型 | 说明 |
|------|------|------|------|
| linux-pam | 1.7.2 | 直接·链接 + 运行期 | `-lpam -lpam_misc`；`pam_start/pam_authenticate/pam_end/pam_strerror`、`misc_conv` |
| systemd | 261 | 直接·链接线（`-lsystemd`） | libsystemd 客户端库；代码路径未编译（见上） |

## 验证结果

```bash
# 构建产物
$ file physlock
physlock: ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
$ readelf -h physlock | grep Machine
  Machine:                           AArch64
$ readelf -d physlock | grep NEEDED
  ... [libpam.so.0] [libpam_misc.so.0] [libsystemd.so.0] [libc.so]

# 运行（安全入口，不触发锁屏）
$ ./physlock -v
physlock 13                 # exit 0
$ ./physlock -h
usage: physlock [-dhLlmsv] [-p MSG]   # exit 0
$ ./physlock -z
physlock: invalid option -- 'z'
usage: physlock [-dhLlmsv] [-p MSG]   # exit 1
```

## 注意事项

- 上游**无自动化测试**（无 `tests/`、Makefile 无 `check`/`test` 目标），见 `reports/upstream-test-entry.md`。
- 运行期需要 `libpam.so.0` / `libpam_misc.so.0` / `libsystemd.so.0`（DT_NEEDED）；由 Conan 依赖链提供。
- physlock 作为 setuid 锁屏工具，实际锁定 VT 需要 root + `/dev/tty0`，本阶段不做真机锁屏（测试仅覆盖 CLI 安全入口）。
---

**编译结束**: 2026-10-13 00:43
**最终状态**: built
