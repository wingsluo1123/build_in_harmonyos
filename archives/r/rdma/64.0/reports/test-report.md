# rdma 64.0 测试报告

- 软件: `rdma` 64.0（上游 linux-rdma/rdma-core v64.0）
- 平台: HarmonyOS PC / OpenHarmony aarch64（`uname -s` = HarmonyOS，OHOS SDK 26.0.0.18，clang 15）
- 测试日期: 2026-10-15
- 构建方式: `conan create`（`ci/conan/profiles/ohos-aarch64`）

## 0. 测试台账总览

| 类别 | 声明数 | 执行数 | 通过 | 阻塞 | 说明 |
|---|---|---|---|---|---|
| 上游 C 测试可执行文件 | 8 | 8 | 4 | 4 | 阻塞项全部因 HarmonyOS PC 无 RDMA 硬件 / 无 `ib_umad` 内核模块 |
| 上游 Python(pyverbs) 测试 | 51 模块 / 384 用例 | 0 | 0 | 384 | `NO_PYVERBS=1` 未构建 pyverbs，且全部依赖真实 RDMA 设备 |
| test_package（本仓新增，消费者+平台专项） | 3 | 3 | 3 | 0 | L1 基础 / 鸿蒙专项 / 消费者用例 |
| **合计已执行** | **11 个二进制** | **11** | **7** | **4** | 新增断言：声明 30 条，本次执行 26 条（4 条未触达：3 条在无设备时不进入的循环内，1 条为 `rindex` 分支另一侧），0 条失败 |

> 上游测试用例「不少报」口径：`rdma_test_executable()` 在 64.0 源码中共 8 处调用
> （`util/tests`、`libibumad/tests`、`libibnetdisc/tests`、`infiniband-diags`），本报告逐项列出；
> pyverbs 的 51 个 `tests/test_*.py` 模块、384 个 `def test_` 方法按源码声明数登记，未实例化的原因见 §3。

## 1. 上游 C 测试（8/8 全部构建并运行）

在构建目录内执行（rdma-core 的测试二进制对 `lib/` 使用相对寻址，须在构建根目录运行）：

| # | 测试二进制 | 源码 | 命令 | 结果 |
|---|---|---|---|---|
| 1 | `bitmap_test` | `util/tests/bitmap_test.c` | `./bin/bitmap_test` | **PASS** rc=0，25 条 `OK` 断言 |
| 2 | `umad_compile_test` | `libibumad/tests/umad_compile_test.c` | `./bin/umad_compile_test` | **PASS** rc=0 |
| 3 | `umad_reg2` | `libibumad/tests/umad_reg2_compat.c` | `./bin/umad_reg2` | **PASS** rc=0（ibwarn: `is ib_umad module loaded?`） |
| 4 | `umad_register2` | `libibumad/tests/umad_register2.c` | `./bin/umad_register2` | **PASS** rc=0（ibwarn 同上） |
| 5 | `ibsendtrap` | `infiniband-diags/ibsendtrap.c` | `./bin/ibsendtrap` | **BLOCKED** rc=255 |
| 6 | `umad_sa_mcm_rereg_test` | `libibumad/tests/umad_sa_mcm_rereg_test.c` | `./bin/umad_sa_mcm_rereg_test` | **BLOCKED** rc=255 |
| 7 | `testleaks` | `libibnetdisc/tests/testleaks.c` | `./bin/testleaks` | **BLOCKED** rc=1 |
| 8 | `mcm_rereg_test` | `infiniband-diags/mcm_rereg_test.c` | `./bin/mcm_rereg_test` | **BLOCKED** rc=139 |

阻塞项证据（均为**环境外部约束**，非适配缺陷）：

```
$ ./bin/ibsendtrap
ibwarn: get_abi_version: can't read ABI version from /sys/class/infiniband_mad/abi_version
        (No such file or directory): is ib_umad module loaded?
ibwarn: get_smi_gsi_pair: Can't open SMI UMAD port (Not supported) (:0)
./bin/ibsendtrap: iberror: failed: Failed to open '(null)' port '0'
exit=255                      # 上游 port 打开失败即 exit(-1)

$ ./bin/umad_sa_mcm_rereg_test
ERR: umad_get_port failed for first IB CA port 0: No error information
exit=255

$ ./bin/testleaks
ibwarn: ... is ib_umad module loaded?
ibnetdisc.c:799; can't open MAD port ((null):0)
discover failed
exit=1

$ ./bin/mcm_rereg_test
ibwarn: ... is ib_umad module loaded?
ERR: Failed to open port
exit=139 (SIGSEGV)            # 上游自身的错误路径
```

HarmonyOS PC 无 RDMA 硬件：`/dev/infiniband` 与 `/sys/class/infiniband` 均不存在，也没有
`ib_umad` 内核模块，因此这 4 个用例在任何 HarmonyOS 设备上都无法通过。

`make check` / `ctest`：上游 CMake **未调用 `enable_testing()`**，`ctest -N` 注册 0 个用例
（上游 C 测试是普通可执行文件，靠人工/打包脚本运行）。本适配的 test_package 由 Conan 自动执行。

## 2. 上游 Python(pyverbs) 测试

- 声明规模：`tests/test_*.py` **51 个模块**，`def test_` 方法 **384 个**
- 实例化数：**0**
- 原因（两条独立约束，缺一不可）：
  1. `NO_PYVERBS=1` —— pyverbs 的 C 扩展需要构建期 Cython + numpy，CI/OHOS 环境仅安装
     Conan（见 SKILL W0b CI 能力矩阵），无法构建；
  2. 全部 pyverbs 用例都需要真实 RDMA 硬件（同一台机器上 `/dev/infiniband` 不存在）。
- 与历史适配一致：本仓 56.1 / 61.0 同样以 `NO_PYVERBS=1` 构建。

## 3. test_package（本次新增 3 个二进制，全部通过）

### 3.1 `test_rdma` — L1 消费者 API 测试（声明 9 条断言，本次执行 7 条）

```
== rdma 64.0 test_package: L1 basic API test ==
  [PASS] device count is not negative
  [PASS] ibv_get_device_list returns a list, or NULL with errno set
  [info] verbs devices: 0 (list NULL: no provider initialised)
  [PASS] device count agrees with the first enumeration
  [PASS] second ibv_get_device_list behaves the same way
  [PASS] rdma_get_devices reports a non-negative count
  [PASS] rdma_get_devices sets errno when it fails
  [info] rdma_get_devices() returned NULL (errno=19, No such device)
  [PASS] rdma_get_devices count matches the returned array
== L1 basic API test: PASS (0 failure(s), verbs=0 cma=0) ==
```

9 条声明中 2 条位于设备遍历循环内（`ibv_get_device_name` 逐设备命名），无 HCA 时循环体不进入，
故本次执行 7 条、0 条失败。覆盖 `ibv_get_device_list` / `ibv_free_device_list` / `ibv_get_device_name` /
`rdma_get_devices` / `rdma_free_devices` 的调用与释放路径。无硬件时
`ibv_get_device_list()` 返回 `NULL` 且置 `errno`（`ibverbs_init()` 失败），
`rdma_get_devices()` 返回 `NULL` + `errno=ENODEV`（无 ucma 模块）—— 断言的是
「API 语义正确」而非「存在设备」。

### 3.2 `test_ohos_specific` — 鸿蒙平台专项测试（声明 21 条断言，本次执行 19 条，**本仓新增，上游无此测试**）

```
T1: package headers + OHOS netlink/socket headers
  [ OK ] sockaddr_storage usable next to <linux/netlink.h>
  [ OK ] netlink header layout intact
  [ OK ] sockaddr_storage complete (not just declared)
  [ OK ] ibv_get_device_list resolved after <linux/netlink.h>
  [ OK ] rdma_get_devices resolved after <linux/netlink.h>
  [ OK ] ibv_get_device_list() callable after sys/socket.h
  [ OK ] rdma_get_devices() callable
T2: program_invocation_short_name substitute
  [ OK ] __progname is non-empty
  [ OK ] __progname carries no path separator
T3: rindex() semantics via strrchr()
  [ OK ] strrchr() finds the last separator
  [ OK ] native rindex() agrees with strrchr()
T4: thread teardown (signal + pthread_kill + join)
  [info] pthread_cancel() present in OHOS libc
  [ OK ] pthread_create()
  [info] worker cancel state=-1 type=-1 (entry points present)
  [ OK ] pthread_kill(SIGUSR1) delivers
  [ OK ] pthread_join() reaps the worker
  [ OK ] signal handler ran on the worker thread
T5: hardware-less enumeration (HarmonyOS PC has no HCA)
  [ OK ] device count is non-negative
  [ OK ] ibv_get_device_list returns a list or sets errno
  [info] RDMA devices present: 0
  [ OK ] second enumeration behaves like the first
  [ OK ] second enumeration agrees with the first
== RESULT: PASS ==
```

21 条声明中 2 条本次未执行：T3 的 `rindex` 存在性分支只走其一（OHOS 运行期 libc 中存在
`rindex`，走 else 分支）、T5 的逐设备命名断言在 0 设备时不进入循环体。

断言项对应的适配点：

| 用例 | 覆盖的适配点 |
|---|---|
| T1 | E119：`-D__MUSL__=1` 使 OHOS `sys/socket.h` 定义 `sockaddr_storage`，与 `<linux/netlink.h>` 同 TU 共存；取函数地址强制链接器解析两族头文件声明的公开符号 |
| T2 | `program_invocation_short_name` → `__progname` 替代可用（E493/E203） |
| T3 | `rindex` 语义等价性；T4 同时证实 OHOS 运行期 libc 确有 `rindex`，而链接期导入库没有 |
| T4 | E513：OHOS 无 POSIX 线程取消（`setcancelstate` 连 `oldstate` 都不写回，实测 `-1`），信号式退出 + `pthread_join` 才能真正回收线程 |
| T5 | 无 HCA 环境下枚举返回 0 设备且幂等，不得报错 |

### 3.3 `test_consumer` — 业务消费者用例（rc 判定，5 处有效性检查）

```
== rdma 64.0 consumer validation (libibverbs + librdmacm public API) ==
libibverbs devices: 0
librdmacm devices: 0
== consumer validation: PASS (rc=0) ==
```

仅使用公开头文件与公开 API（`ibv_get_device_list` / `ibv_get_device_name` /
`ibv_get_device_guid` / `rdma_get_devices`），验证第三方可编译、可链接、可运行。
该用例按「失败即 `return` 非零」判定（两处 API 调用失败、两处逐项有效性校验、最终 `rc==0`），
不打印逐条断言标记，故不计入 §0 的断言数。

## 3.5 检视意见驱动的修正（2026-10-15 迭代）

AI Review（PR #16057）提出 1 项 P2 + 2 项 P3，已全部修正后重新验证：

| 级别 | 位置 | 问题 | 修正 |
|---|---|---|---|
| P2 | `compat/ohos-compat.h` `rdma_ohos_getpass` | 返回前又调用一次 `tcgetattr()`，把「已关回显」的设置重新读入 `saved`，导致终端 ECHO 永不恢复 | 增加 `have_saved` 标志，只在首次 `tcgetattr()` 成功时用它恢复原始 termios |
| P3 | `test_package/test.c` | `num_verbs == 0 \|\| num_verbs > 0` 恒真 | 记录首次枚举结果 `first_verbs`，断言 `num_verbs == first_verbs` |
| P3 | `test_package/test_ohos_specific.c` | `sizeof(struct ibv_device *) > 0` 恒真 | 改为取 `ibv_get_device_list` / `rdma_get_devices` 函数地址断言非空（强制符号解析），并以 `sizeof(struct sockaddr_storage) >= sizeof(struct sockaddr_in)` 校验类型完整 |

## 4. 产物与质量门禁

| 项 | 结果 |
|---|---|
| `conan-verify` G0–G4 | 全部 PASS |
| G3 R26 系统同名库隔离 | PASS（未与 `/lib`、`/lib64` 同名冲突） |
| L5a SONAME 自检（包内 `lib/` 顶层 `lib*.so`） | 11/11 带相对 SONAME，0 缺失 |
| test_package 运行方式 | `VirtualRunEnv` + `self.run(..., env="conanrun")` 等价的显式 `LD_LIBRARY_PATH` 注入 |

包内产物清单：`bin/` 56 个可执行文件、`lib/` 11 个共享库 + 23 个静态库、
`lib/libibverbs/` 18 个 provider、`libexec/` 2、`etc/` 30、`include/` 33。

L5a 自检明细：

```
libefa.so        SONAME=libefa.so.1        libibumad.so     SONAME=libibumad.so.3
libhns.so        SONAME=libhns.so.1        libibverbs.so    SONAME=libibverbs.so.1
libibmad.so      SONAME=libibmad.so.5      libionic.so      SONAME=libionic.so.1
libibnetdisc.so  SONAME=libibnetdisc.so.5  libmana.so       SONAME=libmana.so.1
libmlx4.so       SONAME=libmlx4.so.1       libmlx5.so       SONAME=libmlx5.so.1
librdmacm.so     SONAME=librdmacm.so.1
```

## 5. 未通过项的归因

| 未通过项 | 归因 | 是否可由适配解决 |
|---|---|---|
| `ibsendtrap` / `umad_sa_mcm_rereg_test` / `testleaks` / `mcm_rereg_test` | 需要真实 RDMA HCA 与 `ib_umad` 内核模块；HarmonyOS PC 两者皆无 | 否（环境约束） |
| 51 个 pyverbs 模块 / 384 用例 | `NO_PYVERBS=1`（无 Cython/numpy）+ 需要真实 RDMA 硬件 | 否（需另立 pyverbs 工具链依赖包） |
