# DRAFT-libzc-0.4.3-check-temp-priority — 上游 check 测试套件受限环境启用与真实运行

## 问题

在 OHOS PC（musl）上启用并运行上游 `make check`（Check 框架 0.15.2）时，8 个测试入口全部
以 `check_msg.c:317: Unable to create temporary file for communication; may not have
permissions to do so`（exit 2）失败。表象是「/tmp 不可写」，但直接设置 `TMPDIR` 与
`umask 022` 均无效——R02 曾据此误判为「HMDFS 环境限制」结案，实为机制性误判。

## 根因

Check 0.15.2 `src/check_msg.c` 的 `open_tmp_file()`（HAVE_MKSTEMP 分支）按固定顺序选择
IPC 临时目录：

1. `getenv("TEMP")`
2. `#ifdef P_tmpdir` → `P_tmpdir`（musl 的 `stdio.h:168` 定义 `P_tmpdir "/tmp"`）
3. `getenv("TMPDIR")`
4. `"."`

随后 `mkstemp("%s/check_XXXXXX")`。关键点：musl 定义了 `P_tmpdir` 且其优先级**高于**
`TMPDIR`，而 OHOS 的 `/tmp` 是只读挂载（`errno=30 Read-only file system`，实测 `df /tmp`
为 `/dev/block/dm-0` 100% 满 / erofs 只读语义）。因此只要 `TEMP` 未设置，无论 `TMPDIR`
怎么设都会被第 2 步的 `P_tmpdir=/tmp` 无条件短路，`mkstemp("/tmp/check_XXXXXX")` 必然失败。
`umask 022` 无效是必然的：errno=30 是挂载只读，与文件权限位无关。

## 方案

设置 **`TEMP`** 环境变量（优先级最高的第 1 步）指向实测可写的目录，例如
`TEMP=/path/to/writable/tmp make check`（先 `mkdir` 并实测 `touch` 可写）。
对 Check 框架测试：`TEMP` 覆盖 `P_tmpdir`，`mkstemp` 使用 `<TEMP>/check_XXXXXX` 成功。
可选 `CK_FORK=no`（`srunner_fork_status()` 读取，`"no"` → `CK_NOFORK` 同进程运行，无 IPC
管道），用于需避免 fork/管道语义的场景；断言仍真实执行、失败仍被发现（统计不变）。

## 验证

- 最小复现 C 程序复刻 `open_tmp_file()` 顺序：无 `TEMP` → `mkstemp(/tmp/check_XXXXXX)`
  errno=30 exit 2；仅 `TMPDIR` → 同样 errno=30 exit 2（被 `P_tmpdir` 跳过）；`TEMP` 可写
  目录 → OK exit 0。
- 机制矩阵实测（交付态构建树，check 0.15.2 链接）：基线 8/8 FAIL exit 2；`TEMP` 8/8 PASS
  exit 0；仅 `CK_FORK=no` 8/8 FAIL（仍走 /tmp）；`TEMP`+`CK_FORK=no` 8/8 PASS exit 0。
- 真实统计：basic 6 / file 6 / pwstream 14 / bruteforce 11 / dictionary 5 / reduce 2 /
  plaintext_password 10 / plaintext 2 个 check，共 56 断言 0 失败 0 错误。

## 适用边界

- 适用于所有使用 Check 框架（`make check` + libcheck）且目标环境 `/tmp` 不可写或
  `P_tmpdir` 指向只读目录的库（aide、bitlbee 等）。要求 libcheck 源码版本为 0.15.2 的
  `open_tmp_file()` 顺序（其他版本需先核对宏与顺序）。
- 前提是上游测试已真实启用（`configure.ac` 的 `PKG_CHECK_MODULES([CHECK]...)` 被解析，
  `USE_CHECK=1`、tests 进入 `SUBDIRS`）；未启用时无「通过率」可言。

## 反例与限制

- `TMPDIR` 方案（E002 推荐）在 musl `P_tmpdir` 已定义的环境无效——E002 仅覆盖
  「/tmp 只读」表层，未覆盖 Check 框架的 `TEMP>P_tmpdir>TMPDIR>'.'` 顺序。
- `umask 022` 对只读挂载（errno=30）无效。
- 不得用 `timeout`/`SIGKILL`/伪造 exit 0 制造通过；不得修改上游测试源码或补丁断言。
- `CK_FORK=no` 只改变运行模式，不能替代 `TEMP` 修复（单设 `CK_FORK=no` 仍失败）。
