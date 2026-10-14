# libmtd 2.3.1-3 适配笔记

## 编译环境
- 构建系统: autotools（mtd-utils 2.3.1 源码树，适配目标为其 `lib/` 产出的 libmtd/libubi/libubigen/libscan 四个 C 库）
- 编译日期: 2026-09-29
- 编译器: clang 15.0.4（OHOS PC aarch64 原生）
- 状态: built
- 上游源码: https://infraroot.at/pub/mtd/mtd-utils-2.3.1.tar.bz2 （HTTP 200，864644 字节）
- 版本语义: `2.3.1-3` 为 Debian sid 包版本（上游 mtd-utils 2.3.1 + Debian 修订 3），源码即上游 2.3.1

## 编译步骤

```bash
# 1. config.guess/sub 不识别 HarmonyOS（UNAME_SYSTEM="HarmonyOS"）→ E007 补丁
perl scripts/patch-autotools-ohos.pl config.guess config.sub
#    修正后 ./config.guess → aarch64-unknown-linux-ohos

# 2. configure（禁用全部 CLI 工具，只保留 lib/ 目标；HMDFS execve 信任延迟规避）
CC=clang CFLAGS="-O2 -fPIC" CONFIG_SHELL=/system/bin/sh sh ./configure \
    --prefix=$DEFAULT_PREFIX MKDIR_P="/system/bin/mkdir -p" \
    --without-tests --without-lsmtd --without-jffs --without-ubifs

# 3. 只编库目标（均为 noinst_LIBRARIES，零外部依赖、仅 libc）
make -j1 libmtd.a libmissing.a libubi.a libubigen.a libscan.a
```

产物：libmtd.a(78038B) libubi.a(32406B) libubigen.a(9888B) libscan.a(6700B) libmissing.a(948B)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type` | config.guess 不识别 UNAME_SYSTEM=HarmonyOS | E007：`patch-autotools-ohos.pl` 修 config.guess/sub；禁止 --build/--host 绕过 |
| 2 | configure 报 `missing one or more dependencies`（uuid/openssl/selinux 检测失败） | 全量工具（mkfs.ubifs/jffsX 等）才需要这些可选依赖，本包只交付 lib/ 四库 | `--without-tests --without-lsmtd --without-jffs --without-ubifs` 禁用工具集；四库本身仅链 libc |
| 3 | HMDFS 对新解压脚本 execve 间歇 EACCES | HMDFS 信任延迟 | `sh ./configure` 解释器调用 + `CONFIG_SHELL`/`MKDIR_P` 显式注入 |

## 上游测试清点（R51 申报表）

上游 `tests/` 7 个子目录：checkfs、fs-tests、jittertest、mtd-tests、ubi-tests、ubifs_tools-tests、unittests。
**上游测试资产总数 N=70**：测试源文件 44 个 `.c` + 测试脚本 18 个 `.sh` + 测试模块定义 7 个 `Makemodule.am` + unittests 运行器基础设施（sysfs_mock）1 项。其中 check_PROGRAMS/test_PROGRAMS 注册 40 个测试程序、TESTS 注册脚本与 TEST_BINS。

| 测试 | 数量 | 实测 | 原因 |
|------|------|------|------|
| unittests/mtdlib_test（cmocka，`-Wl,--wrap=open/ioctl/read/lseek/write` mock） | 17 | **17/17 PASSED** | 无需设备，mock ioctl |
| unittests/ubilib_test（cmocka，`--wrap=open/close/ioctl/read/lseek` mock） | 16 | **16/16 PASSED** | 无需设备，mock ioctl |
| 其余测试资产（N=70−33=37）：checkfs(3)/fs-tests(2)/jittertest(4)/mtd-tests(7)/ubi-tests(13)/ubifs_tools-tests(1) 的测试程序与脚本 + 支撑源文件 | 37 | 0（不可运行） | 均需真实 MTD/UBI 内核设备（mtdram/nandsim）；本机 `ls /dev/mtd* /dev/ubi*` → No such file or directory（HarmonyOS PC 用 UFS/NVMe，无 raw flash） |

cmocka 单测编译方式：`clang -O0 -std=gnu99 -Iinclude -DSYSFS_ROOT=... tests/unittests/libmtd_test.c lib/libmtd.c lib/libmtd_legacy.c libcmocka.a -Wl,--wrap=...`，cmocka 取自制品仓 `cmocka/2.0.2`（ohpcd，`conan download` 实证存在）。

## 验证结果

```bash
$ ./mtdlib_test
[==========] tests: 17 test(s) run.
[  PASSED  ] 17 test(s).
$ ./ubilib_test
[==========] tests: 16 test(s) run.
[  PASSED  ] 16 test(s).
$ ./smoke_consumer   # 消费者链接冒烟：libmtd.a+libubi.a+libmissing.a 静态链接 + API 调用
libmtd_open=null libubi_open=null (NULL expected: no /dev/mtd* on OHOS PC)
rc=0
```

运行时语义：OHOS PC 无 `/dev/mtd*`/`/dev/ubi*`，`libmtd_open()`/`libubi_open()` 如实返回 NULL（优雅降级，非崩溃）；嵌入式 OHOS 板级有 raw flash 即可全功能使用。库为纯 ioctl 封装（MTD_MEM* / UBI_IOC*），链接期零外部依赖。

## 依赖版本

无第三方依赖（仅 libc + 内核 UAPI 头 `include/mtd/*.h`、`include/linux/`）；测试期使用制品仓 cmocka/2.0.2。

## 注意事项

- 四库均为上游 `noinst_LIBRARIES`，`make install` 不会安装 → conan 配方在 `package()` 手动拷贝 `.a` 与头文件。
- 上游仅产静态 `.a`（无 -fPIC 也未编 `.so`）；配方按静态库打包（R26 系统同名库静态口径一致）。
- 头文件依赖：`libmtd.h` → `mtd/mtd-user.h`、`mtd/mtd-abi.h`；`libubi.h` → `mtd/ubi-user.h`；`libscan.h`/`libubigen.h` → `mtd/ubi-media.h`、`mtd_swab.h`；`common.h` → `config.h`（configure 生成）。打包头文件须连带 `include/mtd/` 子目录。
- libmtd.a 依赖 libmissing.a 的 execinfo 兼容符号（`backtrace` 等，musl 缺失时启用）→ 消费者须同时链接 libmissing.a（配方合并打包）。
---

**编译结束**: 2026-09-29 20:08
**最终状态**: built
