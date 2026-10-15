# pgtt 4.6 适配笔记（OHOS PC aarch64）

## 目标库信息

| 项 | 值 |
|---|---|
| 软件 / 版本 | pgtt / 4.6（扩展内部版本 4.6.0） |
| 上游仓库 | https://github.com/darold/pgtt |
| tag → commit | `v4.6` → `c8730243ca993de96122641452a138f284ef0437` |
| 源码包 | `https://github.com/darold/pgtt/archive/refs/tags/v4.6.tar.gz` |
| SHA256 | `9d70ebaa0ef091990dd6ec1446e0e7b894507718249cbf07eaaedf384b66bcbe` |
| 语言 | C |
| 构建系统 | make / PGXS（PostgreSQL Extension Building Infrastructure） |
| 产物 | 服务端可加载模块 `pgtt.so` + `pgtt.control` + 41 个 `pgtt--*.sql`（21 基础版 + 20 升级步） |

pgtt 是 PostgreSQL **服务端扩展**（实现 Oracle 风格 GLOBAL TEMPORARY TABLES），
不是独立可执行程序或通用库：`pgtt.so` 由运行中的 postgres 进程在
`CREATE EXTENSION` / `session_preload_libraries='pgtt'` 时 dlopen，模块内
PostgreSQL 服务端符号在该进程中解析。

## 编译环境

- 构建系统: make（PGXS）
- 编译日期: 2026-10-13
- 编译器: `/data/service/hnp/bin/clang`（clang 15.0.4，由 `pg_config --cc` 提供，R33）
- 目标: OHOS aarch64（`os=OHOS`, `os.version=6.0`, `arch=armv8`, `compiler.libcxx=libc++`, `build_type=Release`）
- 强制第三方依赖: `postgresql/18.3`（ohpcd 预编译包；W0 已验证 `conan download` → exit 0）

## 编译步骤

```bash
# 1. 初始化（下载 + 骨架 + 依赖解析）
python3 scripts/ohc-run.py init-build pgtt 4.6 \
    --url=https://github.com/darold/pgtt/archive/refs/tags/v4.6.tar.gz

# 2. 取 postgresql/18.3 预编译包（pg_config + PGXS + 服务端头文件 + 服务端二进制）
conan install --requires=postgresql/18.3 -pr:h/$PROF -pr:b/$PROF -r=ohpcd

# 3. PGXS 真实构建（唯一构建命令）
make PG_CONFIG=<pg包>/bin/pg_config rpathdir='$$ORIGIN/../lib' -j1
# → pgtt.so (ELF64 AArch64, 59776 B)，0 error / 0 warning

# 4. 安装到 PostgreSQL 树 + 启动临时实例
make PG_CONFIG=<pg>/bin/pg_config rpathdir='$$ORIGIN/../lib' install
initdb -D $PGDATA --auth=trust --no-locale -U pgtt
pg_ctl -D $PGDATA -o "-p 5499 -c listen_addresses='127.0.0.1'" -w start

# 5. 上游测试
make PG_CONFIG=<pg>/bin/pg_config installcheck
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | PGXS 构建出的 `pgtt.so` RUNPATH 为构建机 conan 缓存绝对路径（`…/.conan2/p/g…/p/lib`） | PGXS 的 `rpathdir` 默认 `$(libdir)`，而本场景的 `pg_config --libdir` 指向 conan 缓存；`make rpath=` / `make enable_rpath=` 均无效（PG18 的开关是 `enable_rpath`，且 `=` 赋值需命令行覆盖） | 显式传 `rpathdir='$$ORIGIN/../lib'`：模块部署在 `<prefix>/lib/postgresql`，加载时经 `$ORIGIN/../lib` 找到 `<prefix>/lib/libpq.so.5`，RUNPATH 可重定位、可复现 |
| 2 | 无 RUNPATH 时是否仍能加载 | 需要 libpq.so.5（pgtt.so 的 `SHLIB_LINK=$(libpq)` 会引入，虽然源码并未引用 libpq API） | 用 `readelf -d` 确认 `NEEDED = libc.so, libpq.so.5`，并在无 `LD_LIBRARY_PATH` 的干净实例上验证 `CREATE EXTENSION pgtt` 成功 |
| 3 | test_package 里往 conan 缓存中的 `postgresql` 包目录写 `pgtt.so` 第二次即 `PermissionError: [Errno 1] Operation not permitted` | conan 包目录共享且（在 HMDFS 上）拒绝原地覆盖 | harness 先把整个 postgresql 安装 `copytree` 到工作目录，再在私有副本上部署（`test_package/pgtt_test.py: localize_pg()`） |
| 4 | 上游 `make installcheck` 首次以 `PGHOST=<unix socket dir>` 运行时 pg_regress 仍连 `localhost` 失败 | pg_regress 需要 TCP loopback；实例以 `listen_addresses=''` 启动 | 实例改以 `-c listen_addresses='127.0.0.1'` 启动（harness 已内置），20/20 通过 |
| 5 | 上游独立用例 `test/privilege.sql` 与 `test/expected/privilege.out` 不一致（`permission denied for table pg_global_temp_tables`） | **上游测试资产陈旧**：4.6 安全加固后 `sql/pgtt--4.6.0.sql` 撤销了 PUBLIC 对 `pgtt_schema.pg_global_temp_tables` 的写权限，并要求建 GTT 的角色显式 GRANT 该表；`privilege.sql` 只 GRANT 了 schema，`expected/privilege.out` 未同步重生成（其中 `search_path` 行也仍是旧代码格式 `public,pgtt_schema`，现码为 `"$user", public, pgtt_schema`） | 非 OHOS/平台问题。按安装脚本注释补 `GRANT SELECT,INSERT,UPDATE,DELETE ON pgtt_schema.pg_global_temp_tables TO pgtt_user1;` 后全部语句行为与预期一致（见 `reports/03-privilege.*`） |

**源码修改：无。** pgtt 4.6 在 OHOS（aarch64, clang 15）上零补丁即可编译，`patches: {}`。

## 依赖版本

| 依赖 | 版本 | 类型 | 说明 |
|---|---|---|---|
| postgresql | 18.3 | 直接·强制（构建期 + 运行期宿主） | ohpcd 预编译包：`pg_config` + PGXS + `include/postgresql/server` + libpq + postgres/initdb/pg_ctl/psql/pg_regress |
| libpq | 18.6（pgtt.so 的 DT_NEEDED `libpq.so.5`，由 postgresql/18.3 提供） | 直接·强制（链接） | 模块加载时经 RUNPATH `$ORIGIN/../lib` 解析 |
| perl / bison / flex | 5.42.2 / 3.8.2 / 2.6.4 | 传递·build-ctx（libpq 配方） | 构建工具链，均可消费 |

上游要求 PostgreSQL ≥ 12（`META.json: prereqs.runtime.requires.PostgreSQL = 12.0`），18.3 满足。

## 上游测试统计（真实执行）

**测试入口（上游 `Makefile:20-29`）**：`TESTS = 00_init … 19_trigger`；`REGRESS = $(patsubst test/sql/%.sql,%,$(TESTS))`；`REGRESS_OPTS = --inputdir=test`。

| 项 | 值 |
|---|---|
| 测试框架 | pg_regress（PostgreSQL 官方回归框架） |
| 命令 | `make installcheck`（= `pg_regress --inputdir=test --bindir=<pg>/bin --dbname=contrib_regression 00_init … 19_trigger`） |
| 用例总数 | 20 |
| 通过 | **20** |
| 失败 | 0 |
| 跳过 | 0 |
| 通过率 | **100%** |
| 日志 | `reports/02-installcheck.log` |

逐项结果（全部 `ok`）：

```
ok 1  00_init                ok 11 10_foreignkey
ok 2  01_oncommitdelete      ok 12 11_after_error
ok 3  02_oncommitpreserve    ok 13 12_droptable
ok 4  03_createontruncate    ok 14 13_searchpath
ok 5  04_rename              ok 15 14_concurrent_index
ok 6  05_useindex            ok 16 15_security_grants
ok 7  06_createas            ok 17 16_sql_injection
ok 8  07_createlike          ok 18 17_drop_authorization
ok 9  08_plplgsql            ok 19 18_subquery
ok 10 09_transaction         ok 20 19_trigger
1..20
# All 20 tests passed.
```

**test_package 中的上游回归复现**（`conan create` 内，含合并后的 21 组）：

```
test_package/pgtt_test.py: pg_regress passed=21 executed=21 failed=0 skipped=0
  00_init … 19_trigger + harmonyos_feasibility
  # All 21 tests passed.
```

### 未纳入自动化套件的上游用例

- `test/privilege.sql`（上游 README 明确说明"not part of the regression tests run
  with make check install because it need manual changes"，需 `createdb`/`psql`/`diff`
  手动驱动）。**已实际执行**：原始脚本对上游 4.6 的 `test/expected/privilege.out`
  不通过，根因见上表 #5（上游期望文件陈旧）；按 4.6 安装脚本要求补表级 GRANT 后
  行为与预期一致。证据：`reports/03-privilege.upstream.actual.out`、
  `reports/03-privilege.upstream.diff`、`reports/03-privilege.corrected.sql`、
  `reports/03-privilege.corrected.actual.out`。
- `test/bench/*.sql` 为人工基准脚本（`bench_load.sql` / `bench_use_gtt.sql` /
  `bench_use_rtt.sql`），非断言的回归用例，无期望输出文件。

### 鸿蒙特有测试用例

- `test_package/harmonyos_feasibility.{sql,out}`（1 例，≥1 达标）：在 OHOS PC
  aarch64 上验证扩展真实拦截 `CREATE GLOBAL TEMPORARY TABLE`、在
  `pgtt_schema.pg_global_temp_tables` 登记 GTT 定义、并物化会话私有临时副本。

## 验证结果

```bash
# PGXS 构建
$ make PG_CONFIG=<pg>/bin/pg_config rpathdir='$$ORIGIN/../lib' -j1     # exit 0, 0 warning
# 产物
$ readelf -d pgtt.so | grep -E 'NEEDED|RUNPATH'
  (RUNPATH)  Library runpath: [$ORIGIN/../lib]
  (NEEDED)   Shared library: [libpq.so.5]
  (NEEDED)   Shared library: [libc.so]

# 上游回归
$ make PG_CONFIG=<pg>/bin/pg_config installcheck                      # exit 0, 20/20 passed

# conan create（含 test_package）
$ conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... -r=ohpcd   # exit 0
  artifact: pgtt.so ELF64/AArch64, NEEDED=[libc.so, libpq.so.5], RUNPATH=$ORIGIN/../lib
  consumer: CREATE EXTENSION pgtt + GTT interception round-trip
  upstream pg_regress: passed=21 executed=21 failed=0 skipped=0

# 配方门禁
$ python3 scripts/ohc-run.py conan-verify pgtt 4.6                    # exit 0
  G1 PASS / G2 PASS / G3 PASS / G4 PASS / L2 / L4 / L5
```

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/pgtt.so` | 服务端可加载模块（ELF64 AArch64，59776 B） |
| `share/extension/pgtt.control` | 扩展控制文件（`default_version='4.6.0'`, `module_pathname='$libdir/pgtt'`） |
| `share/extension/pgtt--*.sql` | 21 个基础安装脚本（2.0.0 … 4.6.0） |
| `share/extension/pgtt--*--*.sql` | 20 个升级脚本（2.0.0--2.1.0 … 4.5.0--4.6.0） |
| `upstream/test/{sql,expected}` + `upstream/test/privilege.sql` | 上游回归资产（供 test_package 复现） |

## 注意事项

- pgtt 的 GTT 功能要求扩展被**预加载**：`session_preload_libraries = 'pgtt'`
  （或 `shared_preload_libraries`）。仅 `CREATE EXTENSION` 而不预加载时，
  `CREATE TEMPORARY TABLE` 仍按 PostgreSQL 原生语义处理。
- 4.6 起 `pgtt_schema.pg_global_temp_tables` 对 PUBLIC 仅保留 SELECT；
  需要创建/改名/删除 GTT 的角色必须额外获得该表的
  `SELECT, INSERT, UPDATE, DELETE` 授权（见 `sql/pgtt--4.6.0.sql:24-41`）。
- `pgtt.so` 的 `DT_NEEDED` 含 `libpq.so.5`（上游 `SHLIB_LINK=$(libpq)` 引入，
  源码并不调用 libpq API）；RUNPATH `$ORIGIN/../lib` 假定模块部署在
  `$(pg_config --pkglibdir)`、libpq 位于其同级 `../lib`（即 postgresql 包的标准布局）。

## 提交前：门禁例外登记

### 1. PF7 源 URL 闸（已修复，非例外）

`archives/p/pgtt/4.6/conandata.yml` 曾出现 `sources.url` 列表形式（首个条目
`https://gh-proxy.com/...`）——系 `finish` → `ci/conan/build_and_test.sh`
预下载阶段 “mirror fallback rewrite” 的残留（同族知识草稿：
`knowledge/drafts/DRAFT-8543-conandata-comment-url-predl-rewrite.kv`）。
已还原为**单一官方 URL**（`patches: {}` 不变），并在注释中写明“本文件只允许出现
sources.url 一个 URL”。复验 `PF7 源URL: PASS`。
**⚠️ 复发提示**：再次运行 `finish`/W3 会重新注入镜像回退，提交前须重放本修复。

### 2. PF9 分支/路径闸（登记例外，走 `--no-preflight`）

PF9 判定 `archives/p/pgtt/README.md`、`archives/p/pgtt/manifest.yaml`
“缺版本目录层”（`bad = [f for f in arch if len(f.split('/')) < 5]`）。
这是**框架闸门之间的已知矛盾**，不是本 PR 违规：

- `scripts/ohc/preflight.py:570`：PF9 拦下所有 4 段路径；
- `knowledge/ARCHIVE-SPEC.md §6` 与 CI L0k：**要求**软件级
  `README.md / manifest.yaml / commands.json` 三件套；
- 既有权威记录：[`knowledge/drafts/pf9-commands-json-software-level-path-gate-contradiction.kv`](../../../../knowledge/drafts/pf9-commands-json-software-level-path-gate-contradiction.kv)
  （来源 sockstat 0.4.2，2026-10-02），结论为“闸门矛盾、走官方逃生口并登记”；
- 已合入 main 的先例：`archives/t/tal/1.9`、`archives/n/net-tools/2.1`、
  `archives/x/xfsprogs/7.2.0`（均带软件级 `README.md`）。

处置：保留软件级文件，建 PR 时使用官方逃生口
`OHC_PREFLIGHT=0` / `--no-preflight`，并在 PR 正文登记上述证据行号
（**登记例外，非静默跳过**）；禁止把 `commands.json`/软件级文件隐藏、改名或
移入版本目录（会真触发 L0k 红灯）。根治方向（提给主编/框架维护者，不在本 PR 内改
框架文件）：PF9 应放行 `archives/<字母>/<包>/` 直接子级的软件级三件套。
---

**编译结束**: 2026-10-13 00:34
**最终状态**: built
