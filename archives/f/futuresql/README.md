# FutureSQL

FutureSQL 是一个面向 Qt 6 的非阻塞 SQL 数据库框架：所有数据库操作在独立的数据库线程上执行，调用方通过 `QFuture` 获取结果，从而避免在主线程执行 SQL 造成界面卡顿。

## 功能概述

- `ThreadedDatabase::establishConnection()` 建立到 SQLite 等数据库的连接
- `execute()` 执行 DDL/DML 语句，支持绑定 `QVariant` 参数
- `getResult<T>()` / `getResults<T>()` 以自定义或默认反序列化器把查询结果映射为 C++ 结构体
- `runMigrations()` 基于目录中的 SQL 迁移脚本升级数据库结构
- 对外提供 CMake 包 `FutureSQL6` 与目标 `FutureSQL6::FutureSQL`

## OHOS 适配

- **Qt6Sql 来源**：基础 `qtbase` 在 OHOS 上以 `FEATURE_sql=OFF` 构建，配方改用 `qtbase-sql-dbus/6.11.1`（`FEATURE_sql=ON`，自带 `QSQLITE` 驱动插件）。
- **SONAME**：CMake 没有 `Platform/HarmonyOS` 模块，配方注入 `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG`。
- **软链接**：设备存储（HMDFS）拒绝 `symlink(2)`，运行期探测不可用时设置 `CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON`，安装单一未版本化 `libfuturesql6.so`（仍带 `DT_SONAME`）。
- **测试协程**：上游测试使用 QCoro，`qcoro/0.13.0` 以 `test_requires` 引入，不传播给消费者；其真实 `QCoro6Config` 需要排在 CMakeDeps 生成目录之前，才能获得 `qcoro_enable_coroutines()` 宏。
- **ECM**：`ecm/6.26.0` 为构建期 tool_require，`ECM_MODULE_PATH` 由配方手动设置。

## 依赖关系

- 编译依赖：`qtbase-sql-dbus/6.11.1`、`ecm/6.26.0`、`qcoro/0.13.0`（测试）
- 运行依赖：`qtbase-sql-dbus/6.11.1`（Qt6Core、Qt6Sql、QSQLITE 插件）

## 参考资料

- 源码仓库：https://invent.kde.org/libraries/futuresql
- 源码归档（KDE Attic）：https://download.kde.org/stable/futuresql/futuresql-0.1.1.tar.xz
