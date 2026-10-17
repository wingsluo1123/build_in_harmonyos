# prefix

## 简介

`prefix` 是 PostgreSQL 的**前缀范围（prefix range）**扩展，提供 `prefix_range`
数据类型，用于高效的最长前缀匹配检索。典型场景是电话呼叫路由：运营商持有官方
号码段分配表，收到来电号码后需要快速判断该号码归属哪个运营商。

- **上游仓库**: https://github.com/dimitri/prefix
- **License**: PostgreSQL License
- **类别**: 数据库扩展（PostgreSQL server extension，PGXS 构建）

## 功能概述

- `prefix_range` 数据类型，支持 `123`、`123[4-5]`、`[2-3]` 形式的前缀范围表达
- 匹配运算符 `@>`（包含）、`<@`（被包含）、`&&`（相交）、`|`（并）、`&`（交），
  以及比较运算符 `=` `<>` `<` `<=` `>` `>=`
- GiST 操作符类 `gist_prefix_range_ops`，为 `@>` / `<@` 提供索引加速
- `pr_penalty()` 索引惩罚函数、`length()` 前缀长度、与 `text` 的相互 cast
- 从 1.1 到 1.2.0 的扩展升级脚本与 unpackaged 迁移脚本

## OHOS 适配

适配方式为标准 PGXS 构建，**未修改任何上游源码，无补丁**。

| 项目 | 说明 |
|------|------|
| 构建系统 | PGXS（`make PG_CONFIG=<postgresql包>/bin/pg_config rpath=`） |
| 编译器 | clang 15.0.4（OHOS musl 工具链，aarch64） |
| 依赖 | `postgresql/18.3`（提供服务端头文件、pgxs.mk、可重定位 pg_config 及服务端程序） |
| 产物 | `lib/prefix.so` + `share/extension/prefix.control` + `share/extension/prefix--*.sql` |

OHOS 平台要点：

- **`rpath=`**：PGXS 默认给共享库加 `-Wl,-rpath,'$(libdir)'`，会把构建机 conan
  缓存绝对路径写进 `.so`。服务端模块由 postgres 进程 dlopen，rpath 无意义，
  关掉后产物 `DT_NEEDED` 只剩 `libc.so`，可复现。
- **扩展模块只能动态构建**：由服务端 `dlopen`，不存在静态链接形态。
- **无 unix socket**：OHOS 构建的 PostgreSQL 18.3 带 `-DHAVE_NO_UNIX_SOCKETS`，
  部署与测试须以 `unix_socket_directories=''` + TCP loopback 运行。
- **需设 `file_extend_method=write_zeros`**：PG 18 默认用 `posix_fallocate` 扩展
  数据文件，而 OHOS 用户文件系统拒绝 `posix_fallocate`（EACCES），会使 `COPY` /
  多行插入报 `could not extend file ... with FileFallocate(): Permission denied`。
  这是 OHOS 上部署 PostgreSQL 的通用要求，与扩展本身无关。
- **`/tmp` 只读**：测试脚本使用 `$TMPDIR` / `$HOME/tmp` 下的可写工作目录。

部署方式（消费侧）：把 `prefix.so` 放进 PostgreSQL 的 `pkglibdir`，把
`prefix.control` 与 `prefix--*.sql` 放进 `sharedir/extension`，然后
`CREATE EXTENSION prefix;`。

## 依赖关系

| 类型 | 依赖 |
|------|------|
| 构建期 | `postgresql/18.3`（服务端头文件 + PGXS + pg_config） |
| 运行期 | PostgreSQL 服务端（18.x 已验证；上游 CI 覆盖 9.1–19） |

## 参考资料

- 上游仓库：https://github.com/dimitri/prefix
- 上游测试说明：仓库内 `TESTS.md`
- 上游 CI 矩阵：`.github/workflows/regression.yml`（PG 9.1–19）
