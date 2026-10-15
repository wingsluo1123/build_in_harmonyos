# pgtt

## 简介

pgtt（PostgreSQL Global Temporary Tables）为 PostgreSQL 提供 Oracle 风格的
**全局临时表**：表的定义持久保存，数据对每个会话私有，并与原生临时表一样在
会话/事务结束时按 `ON COMMIT PRESERVE ROWS` / `ON COMMIT DELETE ROWS` 清理。
用于从 Oracle 迁移到 PostgreSQL 时不必改写大量使用 GTT 的应用代码。

## OHOS 适配

使用 Makefile + PGXS（PostgreSQL Extension Building Infrastructure）构建，
产出服务端可加载模块 `pgtt.so`（由运行中的 postgres 进程 dlopen）以及扩展的
控制文件与 41 个 SQL 安装/升级脚本。

- 构建依赖 `postgresql/18.3`（ohpcd 预编译包，提供 `pg_config`、PGXS makefile、
  `include/postgresql/server` 头文件与 libpq），无需引入 PostgreSQL 源码。
- 源码零修改（无补丁）即可在 OHOS aarch64（clang 15.0.4）编译。
- `.so` 的 RUNPATH 设为 `$ORIGIN/../lib`（可重定位），部署到
  `$(pg_config --pkglibdir)` 后经同级 `../lib` 解析 `libpq.so.5`。

## 依赖

- PostgreSQL >= 12.0（上游 `META.json` 声明；本归档使用 `postgresql/18.3`）
- 构建期：`pg_config` + PGXS + 服务端头文件（均来自 `postgresql/18.3`）

## 使用

```conf
# postgresql.conf —— GTT 功能需要预加载
session_preload_libraries = 'pgtt'
```

```sql
CREATE EXTENSION pgtt;
CREATE GLOBAL TEMPORARY TABLE t (id integer) ON COMMIT PRESERVE ROWS;
```

创建/改名/删除 GTT 的角色还需要 `pgtt_schema.pg_global_temp_tables` 的写权限
（PostgreSQL 4.6 起的安全加固，见 `sql/pgtt--4.6.0.sql` 注释）：

```sql
GRANT ALL ON SCHEMA pgtt_schema TO app_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON pgtt_schema.pg_global_temp_tables TO app_role;
```

## 测试

- 上游回归：`make installcheck`（pg_regress，20 组 `test/sql/*.sql`）——本归档实测 **20/20 通过**。
- 上游独立用例：`test/privilege.sql`（需手动驱动；上游 4.6 的
  `test/expected/privilege.out` 为加固前陈旧版本，详见 `4.6/notes.md`）。
- 鸿蒙特有：`test_package/harmonyos_feasibility`（1 例，随 `conan create` 执行）。

## 参考

- 上游仓库: https://github.com/darold/pgtt
- 版本笔记: [`4.6/notes.md`](4.6/notes.md)
