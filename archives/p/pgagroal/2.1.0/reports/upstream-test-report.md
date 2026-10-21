# pgagroal 2.1.0 上游测试套件在 HarmonyOS PC 的真实执行报告

- 执行时间：2026-10-17 14:31（本地时间，对应 `reports/upstream-test-run.log` 内时间戳）
- 平台：HarmonyOS PC / aarch64（`aarch64-linux-ohos`）
- 编译器：clang 15.0.4（`/data/service/hnp/bin/clang`），CMake 4.1.2
- 被测对象：`libpgagroal.so` + `pgagroal`/`pgagroal-cli`/`pgagroal-admin` 等 5 个可执行文件，
  由本配方的源码 + 4 枚配方补丁 + 与配方逐项相同的 CMake 参数（`-DHAVE_LINUX=1`、单/复数
  `OPENSSL_INCLUDE_DIR*`、`PGAGROAL_ALLOW_STATIC_DEPS=ON`、Conan 工具链、`-j1`）构建
- 数据库：PostgreSQL 16.10（Conan 制品 `postgresql`，本地 initdb + pg_ctl 启动，端口 15432）
- 运行器：上游自带 MCTF runner `test/runner.c` → `build/test/pgagroal_test`

## 结论

```
=== Test Summary ===
Total tests: 96
Passed: 96
Failed: 0
Skipped: 0
```

上游 10 个 MCTF 套件、96 个用例全部在 HarmonyOS PC 上真实执行并 100% 通过
（进程退出码 0）。逐条 `[PASS]` 输出见 `reports/upstream-test-run.log`。

| 套件（module） | 上游用例数 | 实测通过 |
|----------------|-----------|---------|
| aes | 12 | 12 |
| alias | 4 | 4 |
| art | 16 | 16 |
| configuration | 31 | 31 |
| connection | 2 | 2 |
| deque | 11 | 11 |
| json | 6 | 6 |
| pgbench_init | 2 | 2 |
| startup_validation | 10 | 10 |
| utf8 | 2 | 2 |
| **合计** | **96** | **96（100%）** |

> 日志里出现的两行 `FATAL` 属于 `startup_validation` 套件的**负向用例**预期输出
> （`startup_validation=on` 但未配 `health_check_user`、两个 primary 指向同一
> `system_identifier`），pgagroal 按上游设计拒绝启动，用例判定为 PASS。

## 运行环境的三处平台差异（均不涉及断言逻辑）

上游套件假设自己跑在「有可写 `/tmp`、root 权限、docker/podman」的 Linux CI 上，
HarmonyOS PC 沙箱与之有差异，处理如下：

1. **`/tmp` 是只读挂载**（`/dev/block/dm-0 on /tmp type erofs (ro,relatime)`）。
   `test/testcases/test_aes.c:84` 把 `mkdtemp` 模板写死成 `/tmp/pgagroal_test.XXXXXX`，
   在 OHOS 上必然 `EROFS`。处理：`reports/upstream-test-aes-tmpdir.diff`（1 处、5 行，
   只把模板改为读 `TMPDIR`、缺省仍回退 `/tmp`），运行前 `TMPDIR=/data/storage/el2/base/cache`。
   **断言、被测函数、用例逻辑零改动**。
2. **`$HOME` 在 HMDFS 上不支持 chmod**：`pgagroal_get_master_key()` 要求 `~/.pgagroal`
   恰为 `700`、`master.key` 恰为 `600`，HMDFS 强制 `drwxrws--x`。处理：把 `HOME` 指向应用
   沙箱目录（`/data/storage/el2/base/cache/pghome`，支持正常 chmod），不改代码。
3. **用例经 shell 跑 `pgbench` 时写 `<project>/log/pgbench.log`**
   （`test/include/tsclient.h:44` `PGBENCH_LOG_FILE_TRAIL`）：该目录须预先存在，否则
   `sh: can't create .../log/pgbench.log` 会让 alias/connection/pgbench_init/utf8 共 10 个
   用例连带失败。处理：运行前 `mkdir -p <project>/log`，不改代码。

## 曾观察到的崩溃及其根因（已解决，非本包缺陷）

首轮执行时 `aes` 套件在第一个用例即以 `SIGSEGV` 退出（`exit=139`）。根因链：

1. `/tmp` 只读 → `setup_mock_master_key()` 的 `mkdtemp()` 返回 `EROFS`，函数 `return 1`；
2. 用例首行 `MCTF_ASSERT(setup == 0, cleanup, ...)` 跳转到 `cleanup:`，**越过了**
   `char* ciphertext = NULL; char* decrypted = NULL;` 等带初始化的声明（C 允许，
   但初始化不执行）；
3. 于是 `free(ciphertext)` 释放的是未初始化的栈值 → SIGSEGV。

即：崩溃是第 1 条的连锁结果，上游在「setup 失败」分支上存在释放未初始化指针的健壮性缺陷。
把 1 修掉（可写临时目录）后 12 个 aes 用例全部通过，不再走该分支。

## 上游第 11 项（`test/check.sh` 容器端到端套件）为何未执行

`test/check.sh` 的 `ci` 分支（免容器）实测不可用，三条硬约束均有代码定位：

- `check.sh:328-337` 走 `start_postgresql()`：`sudo cp -R $TEST_PG_DIRECTORY/root /`、
  `mkdir -p /conf /pgconf /pgdata /pgwal /pglog`、`chown -R postgres:postgres …` ——
  需要 root 与可写根目录，沙箱内 uid=20020085、根文件系统为只读 `erofs`；
- `check.sh:337` `$TEST_PG_DIRECTORY/root/usr/bin/run-postgresql-local` 需要上游
  `test/postgresql/src/postgresql17` 源码树与专用 PG 构建产物，worker 上不存在；
- `check.sh:325-355` 依赖 `postgres` 系统用户 + `runuser`/`sudo -E -u postgres`。
- 默认（非 `ci`）路径 `check.sh:83-90` 直接 `exit 1`：`Neither Docker nor Podman is installed.`，
  且 `test/CMakeLists.txt:141` 只在 `if(container)` 下注册 `container_test`，OHOS 上
  CTest 配置期即输出 `Docker or podman needed. The test suite will be skipped.`。

因此该项在 CI worker 上不具备执行条件；连接池运行时行为改由本报告的 96 个 MCTF 用例
（其中 connection/alias/utf8/pgbench_init 共 10 例经真实 PostgreSQL 与运行中的 pgagroal
连接池完成建连、database 别名路由、UTF-8 用户与 pgbench 初始化）覆盖。

## 复现步骤

```sh
# 1) 构建（与配方完全相同参数，含 4 枚配方补丁）
sh reports/upstream-test-runner.sh    # 见脚本内 build 段；也可直接复用 conan 构建目录

# 2) 起本地 PostgreSQL 16.10 + pgagroal 连接池，然后一次跑完整套件
sh reports/upstream-test-runner.sh run
```

脚本要点（与 `run` 段一致）：`TMPDIR=/data/storage/el2/base/cache`、
`HOME=/data/storage/el2/base/cache/pghome`、`mkdir -p <project>/log`，从
`build/test` 目录启动 `pgagroal_test`（二进制 `DT_NEEDED` 是相对路径
`../src/libpgagroal.so`，必须借工作目录解析到本次构建的库）。
