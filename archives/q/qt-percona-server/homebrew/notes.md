# qt-percona-server homebrew 适配笔记

## 编译环境
- 构建系统: CMake + Ninja
- 编译日期: 2026-07-19
- 编译器: clang/clang++
- 状态: built

## 源码信息
- 源码: qtbase-everywhere-src-6.11.1.tar.xz
- 上游: https://download.qt.io/official_releases/qt/6.11/6.11.1/submodules/
- 构建子目录: src/plugins/sqldrivers
- Homebrew formula: https://github.com/Homebrew/homebrew-core/blob/master/Formula/q/qt-percona-server.rb

## 编译步骤

### CMake 配置
```bash
cmake -S src/plugins/sqldrivers -B build -G Ninja \
  -DCMAKE_STAGING_PREFIX=$DEFAULT_PREFIX \
  -DFEATURE_sql_ibase=OFF \
  -DFEATURE_sql_mysql=ON \
  -DFEATURE_sql_oci=OFF \
  -DFEATURE_sql_odbc=OFF \
  -DFEATURE_sql_psql=OFF \
  -DFEATURE_sql_sqlite=OFF \
  -DMySQL_LIBRARY=libperconaserverclient
```

### 编译
```bash
cmake --build build
cmake --install build
```

## 与现有 Qt SQL 驱动的对比

| 项目 | qt-mysql | qt-mariadb | qt-percona-server |
|------|----------|------------|-------------------|
| Qt 版本 | Qt5 (5.12.12) | Qt5 (5.12.12) | Qt6 (6.11.1) |
| 构建方式 | 手动 clang++ | 手动 clang++ | CMake + Ninja |
| 链接客户端库 | libmariadb | libmariadb | libperconaserverclient |
| 输出文件 | libqsqlmysql.so | libqsqlmysql.so | libqsqlmysql.so |
| 驱动键 | QMYSQL3/QMYSQL/QMARIADB | QMYSQL3/QMYSQL/QMARIADB | QMYSQL |

## 依赖版本
- Qt6 Core/Sql: 6.11.1
- Percona Server: 8.0.36 (libperconaserverclient)

## 注意事项
- percona-server 依赖需先适配并发布到 Conan 制品仓（R36）
- 与 qt-mysql、qt-mariadb 冲突，不可同时安装
- 运行时需要 ELF 签名才能通过 dlopen 加载（OHOS 平台限制）
- OHOS 环境可能混合 Qt5/Qt6 headers，需确保 CMake 找到正确的 Qt6 路径

## 交付物

| 文件 | 说明 |
|------|------|
| libqsqlmysql.so | Qt6 Percona Server SQL 驱动插件 |

**编译结束**: 2026-07-19
**最终状态**: built
