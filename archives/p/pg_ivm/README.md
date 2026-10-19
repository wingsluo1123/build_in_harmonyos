# pg_ivm

## 软件描述

pg_ivm 是 PostgreSQL 的**增量物化视图（IMMV, Incremental Materialized
View Maintenance）**扩展。用 `CREATE INCREMENTAL MATERIALIZED VIEW` 创建的
物化视图在基表发生 INSERT / UPDATE / DELETE 时**只增量更新受影响的元组**，
不再每次全量重算，因此能在高频写入场景下把物化视图的维护代价从 O(全表)
降到 O(变更量)。

上游项目：<https://github.com/sraoss/pg_ivm>（License: PostgreSQL）

### 主要特性

- **增量维护**：基表变更即时反映到 IMMV，无需手动 `REFRESH`
- **手动刷新可控**：提供 `refresh_immv()` 支持并发/非并发刷新与语义切换
- **广泛的查询支持**：内连接、外连接、聚合（含 `DISTINCT`、`GROUP BY`、
  `HAVING`）、子查询与 `EXISTS` 等
- **与 PostgreSQL 版本解耦**：单扩展支持多个 PG 大版本（本仓基于 PG 18.3）

### 典型应用场景

- 实时报表 / 仪表盘：基表持续写入，视图随查随新
- 物化视图成本敏感场景：大基表 + 小变更量时避免全量刷新
- 实时风控与统计聚合：对最新数据做近实时聚合查询

## 本仓适配

| 项 | 说明 |
|---|---|
| 版本 | 1.15（上游 tag `v1.15`） |
| 平台 | HarmonyOS PC / OHOS aarch64 |
| 构建系统 | PGXS（Makefile） |
| 配方 | `archives/p/pg_ivm/1.15/` |
| 基线 PostgreSQL | 18.3（配方在 tmpfs 自举，含 HarmonyOS 适配补丁） |
| 上游回归 | 13/13 组通过（4 组 `pg_regress` + 9 组 `pg_isolation_regress`） |

### 适配要点

- 制品仓已发布的 `postgresql/18.3` 包只含客户端面（`bin/psql`、`lib/libpq`），
  不含 `include/server`、`lib/pgxs` 与 `pg_regress`，**无法用于编译或验证扩展**；
  因此配方与 `archives/p/postgresql-topn` 同源，自举一份完整 PostgreSQL 18.3。
- PGXS 必须指向安装树 `install/lib/pgxs/src/makefiles/pgxs.mk`（pgxs.mk 以
  `$(dir $(PGXS))/../..` 解析兄弟文件 `Makefile.shlib`）。
- 扩展引用的 PG 服务端符号在 `CREATE EXTENSION` 时由 postgres 进程提供，
  链接期需 `PG_LDFLAGS="-Wl,--unresolved-symbols=ignore-all
  -Wl,--allow-shlib-undefined"`。
- HarmonyOS 上 Unix socket 不可用，回归在 TCP 回环集群 + staging
  `extension_control_path`/`dynamic_library_path` 下运行。

详见 `1.15/notes.md`。
