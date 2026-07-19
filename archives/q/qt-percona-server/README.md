# qt-percona-server

## 简介
qt-percona-server 是 Qt6 的 Percona Server SQL 驱动插件，从 qtbase 6.11.1 源码的 `src/plugins/sqldrivers/mysql` 目录构建。生成 `libqsqlmysql.so`，链接 Percona Server 客户端库（libperconaserverclient.so）作为后端，支持 QMYSQL 驱动键。

## OHOS 适配
- 从 qtbase 6.11.1 源码单独构建 mysql sqldriver 插件
- 使用 CMake + Ninja，仅启用 `FEATURE_sql_mysql=ON`，其余 SQL 驱动全部 OFF
- 指定 `MySQL_LIBRARY` 为 percona-server 的 libperconaserverclient.so
- 运行时 dlopen 加载驱动需要 ELF 签名（OHOS 平台限制）

## 与其他 Qt SQL 驱动的关系
| 包 | Qt 版本 | 链接库 | 冲突 |
|---|---|---|---|
| qt-mysql | Qt5 | libmysqlclient / libmariadb | 是 |
| qt-mariadb | Qt5 | libmariadb | 是 |
| qt-percona-server | Qt6 | libperconaserverclient | 是 |

三者均安装相同的 `libqsqlmysql.so`，不可同时安装。

## 依赖
- 编译依赖：qtbase/6.11.1 (headers + libraries)、percona-server (libperconaserverclient 开发库)
- 运行依赖：Qt6Sql、Qt6Core、libperconaserverclient

## 参考
- Homebrew formula: https://github.com/Homebrew/homebrew-core/blob/master/Formula/q/qt-percona-server.rb
- Qt6 SQL 驱动文档: https://doc.qt.io/qt-6/sql-driver.html
- Percona Server: https://github.com/percona/percona-server
