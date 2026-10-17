# prefix 1.2.11 鸿蒙 PC 适配笔记

## 编译环境

- 目标平台：OHOS / HarmonyOS PC（aarch64，HongMeng Kernel）
- 构建系统：PGXS（PostgreSQL 扩展标准构建）
- 编译器：clang 15.0.4（`/data/service/hnp/bin/clang`，Target: aarch64-unknown-linux-ohos）
- 依赖：`postgresql/18.3`（conan，OHOS/aarch64 已发布 binary）
- 构建日期：2026-10-16

## 源码信息

- 上游版本：1.2.11（tag `v1.2.11`）
- 官方源码 URL：`https://github.com/dimitri/prefix/archive/refs/tags/v1.2.11.tar.gz`
- SHA256：`3ed7588cfb2f1c7a29b6a682a4bc4fc3d7a4b4c8dbacae04f4b4aea01fc5eed9`
- 上游 commit：`413f00607c3c3446e4f804ef1874a98caefabd4d`
- License：PostgreSQL License

## 软件简介

`prefix` 给 PostgreSQL 增加 `prefix_range` 数据类型，用于高效的最长前缀匹配。
支持 `123`、`123[4-5]`、`[2-3]` 形式的前缀范围，提供 `@>` `<@` `&&` `|` `&`
等运算符与 `gist_prefix_range_ops` GiST 操作符类。典型用途是电话呼叫路由：
用官方号段分配表把来电号码解析到归属运营商。

## 为什么它是数据库扩展而不是普通库

产物 `prefix.so` 是 **服务端**模块，由 postgres 进程在 `CREATE EXTENSION` 时
`dlopen`，所有 PostgreSQL 符号都在该进程内解析。因此：

- 不存在"链接进可执行文件"的用法，`shared` 是唯一有效形态；
- 交付物除了 `.so`，还必须包含 `prefix.control` 与 `prefix--*.sql` 安装脚本；
- 有效性只能在**运行中的服务端**里验证 —— 这也是 test_package 会起一个真实
  PostgreSQL 实例的原因。

## 构建步骤

```bash
# 1. 依赖（已发布 binary，无需源码构建）
conan download postgresql/18.3 -r=ohpcd --only-recipe
conan install --requires=postgresql/18.3 -r=ohpcd \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=never

# 2. 编译 + 测试（配方自动完成 PGXS 构建、打包、上游回归与消费者测试）
conan create archives/p/prefix/1.2.11 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -r=ohpcd
```

配方内实际执行的构建命令：

```bash
make PG_CONFIG="<postgresql包>/bin/pg_config" rpath= -j1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 产物 `.so` 里带构建机绝对路径 | PGXS `Makefile.global` 的 `rpathdir = $(libdir)` 默认给共享库加 `-Wl,-rpath,'$(libdir)'` | 传给 make `rpath=` 覆盖为空。服务端模块由 postgres 进程 dlopen，rpath 无意义；关闭后 `DT_NEEDED` 只剩 `libc.so`，产物可复现 |
| 2 | 服务端起不来 | OHOS 构建的 PostgreSQL 18.3 配置含 `-DHAVE_NO_UNIX_SOCKETS`，没有 unix socket 支持 | 启动参数加 `-c unix_socket_directories=''`，走 TCP loopback（`listen_addresses=127.0.0.1`）；客户端用 `-h 127.0.0.1` |
| 3 | 直接运行 pg_regress 报 `Error loading shared library libpq.so.5` | 包内 `pg_regress` 位于 `lib/postgresql/pgxs/src/test/regress/`，其 RUNPATH（`$ORIGIN/../lib`）只对 `bin/` 下的可执行文件有效 | 运行前 `export LD_LIBRARY_PATH=<pgroot>/lib` |
| 4 | `prefix.sql` 用例报找不到 `prefixes.fr.csv` | 该用例用 psql 客户端相对路径 `\copy`，解析基准是 pg_regress 的 cwd；PostgreSQL 自己的回归套件也避免依赖 cwd（上游 `src/test/regress/sql/copy.sql` 用 `\getenv` 取绝对路径） | 测试脚本在执行前把该路径字面量固定为绝对路径，并在 `sql/` 与 `expected/` 中同步替换（保证 psql 回显逐行匹配）；归档内保存的测试文件与上游逐字节一致 |
| 5 | `explain` 用例若单独运行必然失败 | 上游 `REGRESS` 存在数据依赖：`explain.sql` 查询 `prefix.sql` 建的 `ranges`/`numbers` 与 `falcon.sql` 建的 `tst` | 按上游 `REGRESS` 声明顺序整组重放，不拆分、不并行 |
| 6 | 服务端报 `could not extend file "base/16384/16455" with FileFallocate(): Permission denied`（HINT: Check free disk space；该 relfilenode OID 随集群与运行而异，另一次复现为 `base/5/16384`），COPY 装到第 3000 行中断 | **不是磁盘空间问题**（`stat -f` 实测同目录仍有约 639 GB 可用）。PG 18 新增的 `file_extend_method` 默认取 `posix_fallocate`，而 OHOS 的用户文件系统拒绝 `posix_fallocate`（实测 `python3 -c "os.posix_fallocate(...)"` 返回 `EACCES`），普通 `write()+fsync()` 正常。于是 `COPY` / 批量插入在需要成批扩展数据文件时（`mdzeroextend()` 无回退分支）直接 ERROR，而单行 `INSERT ... SELECT` 不受影响——这解释了同一套回归里 `falcon`（99999 行单行插入）通过、`prefix`（`\copy` 多行插入）失败的现象 | 服务端启动加 `-c file_extend_method=write_zeros`，改走零填充写入路径。这是 OHOS 上部署 PostgreSQL 的**通用**运行时要求，与扩展本身无关，已写入 README 与 MANIFEST |

上游源码本身**未做任何修改**，本版本无 `patches/` 目录。编译期仅出现上游自带的
一处告警（`prefix.c:538: unused function 'pr_contains_prefix'`），不影响产物。

## 测试说明

### 上游回归套件

上游用 PGXS 的 `REGRESS` 驱动，唯一入口 `make installcheck`：

```
Makefile:8  REGRESS = create_extension prefix falcon $(EXPLAINSQL) queries
```

共 **5 个用例**（`EXPLAINSQL` 在 PG 9.0+ 取 `explain`）。上游 CI 在
PG 9.1–19 全矩阵运行（`.github/workflows/regression.yml`）。本适配在
PostgreSQL 18.3 上以 pg_regress 整组重放，**5/5 通过**。

用例内容：

| 用例 | 覆盖 |
|------|------|
| `create_extension` | `CREATE EXTENSION prefix` 装载服务端模块 |
| `prefix` | 装载 11966 行官方号段表 → 建 `prefix_range` 表 + GiST 索引；`@>`/`<@` 对称性（Debian Bug 690160）、`pr_penalty` 单调性、号码 join 命中数 |
| `falcon` | 10 万行号段的 GiST `<@` 检索，顺序扫描与索引扫描结果一致（各 1000 行） |
| `explain` | 最长前缀匹配查找与索引检索的执行计划校验 |
| `queries` | 运算符语义、传递性、集合运算 `|`/`&`、类型 cast 与 `length` |

### 消费者端到端测试（鸿蒙特有）

`test_package/run_pg_test.sh` 在隔离的 PostgreSQL 18.3 实例（从 conan 缓存整体
拷出，缓存保持干净）中，装入**本配方安装后的**产物并执行：

- **CONSUMER-1（规则 12 完整消费者用例）**：FR 电话号段路由。真实输入是
  `prefixes.fr.csv`（法国电信监管机构公布的官方前缀分配表，11966 行）；流程是
  建前缀表 → 建 `prefix_range` 表与 GiST 索引 → 构造 5000 个待路由号码 →
  用 `@>` 运算符做最长前缀匹配解析归属运营商；业务输出核对为
  `routed=2019 / matched=2019 / 0146640123→FRANCE TELECOM/0146 /
  0100091234→LONG PHONE/010009`，并额外要求「走索引」与「走顺序扫描」两条
  互相独立的执行路径结果集零差异（`diff_ix_seq=0`），且执行计划确实命中
  `idx_prefix`。
- **OH-1**：`CREATE EXTENSION prefix` 在 OHOS 原生 postgres 服务进程中装载模块。
- **OH-2**：产物 ABI —— ELF AArch64、`DT_NEEDED` 仅 `libc.so`、无构建机 RUNPATH。
- **OH-4**：包内产物与隔离实例 pkglibdir 内实际加载的 `prefix.so`，都必须等于
  `test_package/MANIFEST.yml` 锚定的 `artifact_sha256`（确认被测对象确为本次配方
  安装后的包）。该锚点是构建产物的**可复现性/回归冻结值**（本机两次独立构建实测
  一致），不是外部独立真值。

## 知识积累

- PostgreSQL 扩展（PGXS）的完整构建依赖可由 conan `postgresql` 包提供：服务端
  头文件 `include/postgresql/server`、`pgxs.mk`、可重定位 `pg_config`；`build()`
  无需构建 PostgreSQL 源码。
- `make rpath=` 是消除 PGXS 默认 rpath 的关键（服务端模块场景通用）。
- `REGRESS` 顺序可能承载用例间的数据依赖，重放时必须整组按序执行。
- 客户端 `\copy` 的相对路径在 pg_regress 下不可依赖 cwd，需固定为绝对路径。
- OHOS 上的 PostgreSQL 18.3 无 unix socket，必须显式走 TCP。
- **OHOS 文件系统拒绝 `posix_fallocate`（EACCES）**，而 PG 18 的 `file_extend_method`
  默认就是 `posix_fallocate`；凡走 `mdzeroextend()` 的成批文件扩展（`COPY`、多行
  插入）都会以 `could not extend file ... with FileFallocate(): Permission denied`
  失败。部署与测试必须显式传 `-c file_extend_method=write_zeros`。可通过
  `EXPLAIN`/行数判断失效点：单行 `INSERT ... SELECT` 正常而 `COPY` 中途中断即是
  该问题。附带教训：错误提示的 HINT 是 "Check free disk space"，但根因与空间无关，
  必须用 `stat -f` 实测可用块而不是照信提示。
---

**编译结束**: 2026-10-16 10:07
**最终状态**: built
