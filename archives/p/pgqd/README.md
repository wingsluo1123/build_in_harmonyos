# pgqd — PgQ 队列维护守护进程

pgqd 是 [PgQ](https://github.com/pgq/pgq)（PostgreSQL 上的基于队列的事件系统）的维护守护进程。
它周期性驱动 `pgq.ticker()` 让队列持续产生 tick，并执行队列表的维护与轮转（maint/rotation），
使队列在长时间运行后不会因表膨胀而退化。本归档将其适配到 HarmonyOS PC（arm64）平台。

## 功能概述

- **可执行程序**：`pgqd`（守护进程，支持 `-d` 启动、`-s` SIGINT 停止、`-r` SIGHUP 重载、`-V` 版本、`--ini` 打印样例配置）
- **配置文件**：`[pgqd]` 段，支持 `logfile` / `pidfile` / `base_connstr` / `database_list` / `initial_database` / `check_period` / `maint_period` / `retry_period` / `ticker_period` 等
- **运行依赖**：libevent（事件循环）、libpq（连接 PostgreSQL）

## 安装后使用

```bash
# 打印样例配置
pgqd --ini > pgqd.ini

# 前台/后台启动（日志与 pidfile 由配置指定）
pgqd -d pgqd.ini

# 重载配置 / 停止
pgqd -r pgqd.ini
pgqd -s pgqd.ini
```

数据库连接通过 `base_connstr` 指定，例如 `host=127.0.0.1 port=5432 user=pgq`。

## OHOS 适配要点

构建系统是 **antimake**（上游自研的手写 Makefile 链，非 automake），因此配方用
`basic_layout(self, build_folder=".")` 强制源码内构建——`Makefile` 以相对路径
`include lib/mk/antimake.mk`，源码外构建会直接失败。

四个可移植性补丁，无平台空壳逻辑、无业务改动：

| 补丁 | 内容 |
|------|------|
| `0001-Makefile.patch` | man page 依赖 rst2man（python3-docutils），OHOS 无该工具；改为仅在 rst2man 存在时生成并安装，否则优雅跳过（有工具时行为与上游一致） |
| `0002-config.guess.patch` | 随包的 config.guess（2018）不认识 HarmonyOS；新增 `*:HarmonyOS:*:*` 分支输出 `aarch64-unknown-linux-ohos` |
| `0003-config.sub.patch` | config.sub 接受 `linux-ohos` 作为合法 OS |
| `0004-configure.patch` | configure 用 `umask 077` 创建 config.status 临时目录，HMDFS 下会 Permission denied；改为 `umask 022` |

源码取自上游官方 release 资产 `pgqd-3.5.tar.gz`（`make dist` 产物，内含预生成
`configure` 与 libusual 子模块内容）。

## 依赖

- `libevent/2.1.13`
- `libpq/18.6.1`（随包提供 `pg_config`，configure 阶段用于定位 libpq）

## 验证

- 上游 `tests/test.sh` 共 6 个用例，其中 4 个（version / show_ini / stop / reload）在真机 + 真实 PostgreSQL 16.10 上运行通过；另外 2 个（ticker / maint）需要 PgQ 扩展（`create extension pgq`），OHOS 无该扩展包，无法运行。
- 真机端到端消费者用例 `test_package/test_pgqd.sh`：现场拉起真实 PostgreSQL 集群，pgqd 以守护进程连库运行，覆盖启动 → 连库 → SIGHUP 重载 → SIGINT 停止全流程。

详见 `3.5/notes.md`。
