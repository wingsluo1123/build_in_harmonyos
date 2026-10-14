# libmtp 1.1.21 适配笔记（Conan 框架重建版）

适配日期：2026-09-30（Windows 阶段 1 产出，状态 prepared）
依赖任务：libmtp 为 mtpfs/1.1 的 R36 必需依赖（mtpfs configure.ac:10
`PKG_CHECK_MODULES(LIBMTP, libmtp >= 1.0)`）。

## W0 依赖分析

| 依赖 | 类型 | 依据 | 处理 |
|------|------|------|------|
| libusb-1.0 >= 1.0.0 | 必需 | configure.ac:116 `PKG_CHECK_MODULES(LIBUSB, libusb-1.0 >= 1.0.0)` | requires `libusb/1.0.27`（归档已有配方；conan 名 `libusb`，pkg_config_name=`libusb-1.0`，PkgConfigDeps 直接生成 configure 需要的 .pc） |
| libgcrypt | 可选（仅 MTPZ） | configure.ac MTPZ 分支 | `--disable-mtpz` 显式关闭，不进依赖图 |
| udev/systemd | 可选（仅 Linux udev 集成） | USE_LINUX 分支安装 udev 规则与 mtp-probe | 构建产物保留，安装路径重定向进包内（见下） |

R35/R36 核验：`conan download "libusb/1.0.27"` 制品仓可用性由 MateBook
阶段终验（Windows 不冒充真机结论）。

## W0b 历史核验（旧格式条目，2026-05-26 真机成功）

`archives/l/libmtp/1.1.21` 旧格式条目（notes/hints）记录了 2026-05-26
真机整链构建成功（clang 15.0.4、libusb-1.0.27、mtp-detect 输出正常）。
关键经验与本配方的取舍：

| 旧补丁 | 内容 | 本配方处理 |
|--------|------|-----------|
| 0001 config.guess / 0002 config.sub | OHOS 平台识别 | **不再需要**：显式 `--build/--host=aarch64-unknown-linux-gnu` 绕开 config.guess（D4：libtool 在 configure:4676 无条件调用它，见构建适配要点 4） |
| 0003 examples-pathutils.c | pathutils.c 平台兼容 | **保留概念，重写为 0001-examples-pathutils-rindex.patch**：`rindex()` → `strrchr()`（musl 无 legacy rindex，examples/pathutils.c:138） |
| 0004 libmtp.pc | pkgconfig 修正 | **不再需要**：Conan 流程 .pc 由 cpp_info/pkg_config_name 生成，安装内 .pc 的前缀由 configure 以实际 prefix 展开 |
| 0005 gphoto2-endian.h | endian.h 兼容 | **不再需要**：gphoto2-endian.h 由 configure（AC_NEED_BYTEORDER_H）按探测结果重新生成 |
| 0006 configure-hmdfs-tmpdir | HMDFS 临时目录 | **改为 build() 内联 sed**（E011，见下） |

hints/ 保留旧手工流程（configure.sh 的 TMPDIR/PKG_CONFIG_PATH 思路已
由配方 generate() 承接）。

## 构建适配要点

1. **E011**：configure:18485 `(umask 077 && mktemp -d "./confXXXXXX")`
   在 HMDFS 上 077 去掉 group 写位后目录不可写（libfuse/termrec 同类）。
   build() 内 `replace_in_file` sed umask 077→022。
2. **E386**：SDK bash getcwd 在 HMDFS 构建目录失败 → 环境注入
   `SHELL=/bin/sh`、unset `CONFIG_SHELL`（termrec §12.38① 先例）。
3. **udev 绝对路径**：USE_LINUX（编译期探测 `__linux__`，OHOS clang
   定义之）→ 顶层 Makefile.am 会把 udev 规则与 mtp-probe 装到
   `@UDEV@`（默认 /usr/lib/udev；旧条目实机记录"只读文件系统安装失败"）。
   `--with-udev=${prefix}/lib/udev`——make 展开 `${prefix}` 为安装前缀，
   零补丁解决。
4. **无 AC_CANONICAL_HOST 但 libtool 无条件调 config.guess**：configure:4676
   的 libtool 探测在 2021 版 config.guess 下不认 uname=HarmonyOS（真机首验
   D4：cannot guess build type）→ 显式
   `--build/--host=aarch64-unknown-linux-gnu`（termrec §12.1 同款）；
   CC/CFLAGS/LDFLAGS 仍由 AutotoolsToolchain 注入。
5. **OHOS musl 忽略 DT_RUNPATH**：configure 的 conftest 测试程序运行期找不到
   libusb-1.0.so.0（errno 127 伪装成 "cannot run C compiled programs"，
   真机首验 D3，config.log 实为 Error loading shared library）→ generate()
   把依赖包 libdirs 注入 LD_LIBRARY_PATH（termrec §12.38③ 同款）。
5. **库形态**：shared/fPIC 双选项，`--enable/--disable-shared/static`
   （libusb/1.0.27 同款参数）；shared 产物走 binary-sign-tool 自签名
   （libusb 先例）。
6. **R9**：make -j1（Autotools.make 默认非并行）。

## 测试（R51 三步法）

上游**零测试**：全部 Makefile.am（顶层/src/examples/util/doc）均无
check_PROGRAMS/TESTS、无 make check 目标、configure.ac 无
AC_CONFIG_TESTDIR；examples/ 是 17 个 CLI 工具（bin_PROGRAMS），不是
测试。依 TEST_QUALITY_SPEC：说明原因并由 test_package 补充消费者测试
（真实编译链接安装后的 libmtp + 传递 libusb-1.0 符号闭包，断言
LIBMTP_VERSION_STRING 与 LIBMTP_Detect_Raw_Devices() 枚举路径完整
运行；细节见 test_package/MANIFEST.yml）。

## 真机第 1 轮验证记录（2026-09-30，SHA 5d273edc2，中止于 export）

conan create 在 export 阶段崩溃（'str' object has no attribute 'get'），
逐轮隔离定位 4 个缺陷（完整报告与 4 轮日志在 MateBook
work/verify-logs/libmtp-defect-report.md、libmtp-probe-create{,2,3,4}.log）：

| # | 缺陷 | 修复（探针全链验证过） |
|---|------|------|
| D1 | conandata patches 用了字符串条目，export_conandata_patches 需 dict | patches 改 dict 条目（patch_file/patch_description/patch_type） |
| D2 | 默认 profile 缺 os.version（环境项，非配方缺陷） | MateBook 命令固定带 `-pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=同` |
| D3 | conftest 运行期找不到 libusb-1.0.so.0（OHOS musl 忽略 DT_RUNPATH） | generate() 注入依赖包 libdirs → LD_LIBRARY_PATH（termrec §12.38③） |
| D4 | libtool 无条件调 config.guess 失败（configure:4676，2021 版不认 uname=HarmonyOS） | 显式 --build/--host=aarch64-unknown-linux-gnu（termrec §12.1）；W0 原判断"不传三元组"已更正，docstring/manifest 同步修订 |

同时证实：上游零测试成立（5 个 Makefile.am 均无 check_PROGRAMS/TESTS）；
R35 libusb/1.0.27 **完整 download rc=0 → 二进制级证实 OHOS 包存在**；
消费者探针 rc=0（detect err=5, num=0——LIBMTP_ERROR_CONNECTING，枚举路径
完整运行，属可接受终态）；L0j libmtp/* 0 配方无重复。

## 真机第 2 轮验证记录（2026-10-01，SHA dda57d22a，中止于 export）

第 1 轮 4 缺陷中 D3/D4 落地核实通过（读码确认），D1 修复引入回归：
dict 化 patch 条目时 `patch_file` 丢了 `patches/` 前缀，
export_conandata_patches 按配方根目录解析 → Patch file does not exist，
create 在 export 阶段即崩溃（本轮全部结果作废）。修复：`patch_file`
恢复 `patches/0001-examples-pathutils-rindex.patch`（与仓库兄弟配方及
Windows 探针版本一致）。同提交收紧 test_libmtp.c 可接受错误集为
NONE/NO_DEVICE_ATTACHED/CONNECTING（与 test_package/MANIFEST.yml 声明
一致，消除 MEMORY_ALLOCATION 多余项）。

## 留给 MateBook（第 3 轮，对新 SHA）的验证项

1. `conan create archives/l/libmtp/1.1.21`（**带 CI profile，D2**）：
   configure（三元组过 libtool 探测、conftest 找到 libusb-1.0.so.0、
   pkg-config 解析 libusb-1.0.pc、umask sed 生效、--with-udev 展开）→
   make -j1 → install。
2. `conan test`：test_package 消费者编译链接 + 真机运行（预期与探针一致：
   smoke passed，detect err 属 NONE/NO_DEVICE_ATTACHED/CONNECTING 之一）。
3. `ohc-run.py finish libmtp 1.1.21 built`。
4. `pre_pr_audit.py` 审计，P0/P1 清零（注意 docstring/manifest 与配方行为
   一致性——本轮已同步修订三元组相关表述）。
5. 回写提交 fast-forward push（SSH）→ 回传回写 SHA。

## 预期真机风险点

- PKG_CONFIG_PATH 注入方式沿用 mtpfs 先例（configure_args 显式传）。
- 若 install 阶段仍有 udev 路径写入（${prefix} 未按预期展开），fallback：
  检查 Makefile 的 udevdir 变量取值并改为 `--with-udev=<package_folder>/lib/udev`。
- examples/ 17 个工具随默认安装（Makefile.am `SUBDIRS=src examples util doc`，
  上游无禁用开关，已核对）；udev 规则内容中 `-p"@UDEV@"` 为规则文件内的
  探测器路径字符串，不影响安装位置正确性。
---

**编译结束**: 2026-10-03 21:21
**最终状态**: built
