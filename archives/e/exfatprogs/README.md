# exfatprogs

exFAT 文件系统工具（三星维护的官方实现）：`mkfs.exfat`、`fsck.exfat`、
`tune.exfat`、`exfatlabel`、`dump.exfat`、`exfat2img`。

- 上游：<https://github.com/exfatprogs/exfatprogs>
- 许可：GPL-2.0-or-later
- 语言 / 构建系统：C / Autotools（release tarball 自带 `configure`）
- 已归档版本：`1.4.3`

## HarmonyOS PC 适配要点

1. `lib/libexfat.c:exfat_cmp_kernel_ver()` 用 `sscanf("%hu.%hu.%hu")` 从
   `uname().release` **头部**取版本号，而本机 release 为
   `HongMeng Kernel 1.12.0` ⇒ 解析失败 ⇒ 全部工具
   `failed to get kernel version.` / `failed to open <image>. -1` 拒绝运行；
   只修解析还不够 —— 解析出的 `1.12.0` 又低于上游 `MIN_KERNEL_VER {2,6,0}`，
   第二层会再以 `pre-2.6 kernel version not supported` 拒绝。
   补丁 `patches/0001-…` 以 **release 是否以数字开头** 判定“版本不可评估 → 放行”，
   Linux release 仍走原闸，且不注入任何平台宏。
2. 硬依赖 `libblkid`（`PKG_CHECK_MODULES([BLKID], [blkid >= 2.20])`）：
   `PkgConfigDeps` + `PKG_CONFIG_PATH` 指向 generators 目录（E468）。
3. 上游 `#include <blkid.h>` 依赖发行版 `blkid.pc` 的 `-I${includedir}/blkid`，
   conan 生成的 `blkid.pc` 只有 `-I${includedir}` ⇒ 配方把
   `-I<libblkid>/include/blkid` 追加进 `CPPFLAGS`。
4. `config.guess` 不识 HarmonyOS（E007）⇒ 传 `--build=aarch64-unknown-linux-gnu`。
5. HMDFS `umask 077` 临时目录不可写（E011）⇒ 配方内把 configure 的
   `(umask 077 && …)` 放宽为 `022`。
6. E386：每条 configure/make/install 以 `env -u CONFIG_SHELL SHELL=/bin/sh …` 执行。
7. R9/E074：串行 `make -j1`（并行 jobserver fifo 撞 HMDFS EPERM）。
8. 上游测试真实执行：`make check`（automake 侧，上游未注册任何 TESTS）+
   `lib/tests/suite0000-bitmap`（5 个单元测试函数）+
   `tests/test_fsck.sh`（19 个镜像 fixture + 4 个 upcase 脚本 = 23 例）。
   后两者上游都没有接进 `SUBDIRS`/`TESTS`，必须由配方显式驱动。

## 能力面（如实记录）

`mkfs.exfat` / `fsck.exfat` / `dump.exfat` / `exfatlabel` 在**普通文件镜像**
（`S_ISREG` 路径）上完整可用，非特权即可运行，这也是本交付的断言面。
块设备与挂载面（`/dev/loop*`、`losetup`、`mount`）对非特权用户不可用
（实测 `/sys/dev/block` 读取 `Permission denied`），**不属本交付断言面**。
