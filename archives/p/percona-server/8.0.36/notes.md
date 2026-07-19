# percona-server 8.0.36 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-07-19
- 编译器: clang/clang++
- 状态: built

## 源码信息
- 源码: percona-server Percona-Server-8.0.36-28.tar.gz (454.7 MB)
- 上游: https://github.com/percona/percona-server
- 构建范围: 仅客户端库 (WITHOUT_SERVER=ON)

## 编译步骤

### CMake 配置
```bash
cmake -S src -B build \
  -DWITHOUT_SERVER=ON \
  -DWITH_SSL=system \
  -DWITH_ZLIB=system \
  -DWITH_BOOST=<boost-package>/ \
  -DOPENSSL_ROOT_DIR=<openssl-package>/ \
  -DZLIB_ROOT=<zlib-package>/ \
  -DCMAKE_POSITION_INDEPENDENT_CODE=ON
```

### 编译
```bash
cmake --build build --target mysqlclient
```

## 与同类配方对比
| 项目 | mariadb-connector-c | percona-server |
|------|---------------------|----------------|
| 源码大小 | ~8 MB | ~455 MB |
| 构建范围 | 完整客户端库 | 仅客户端库 (WITHOUT_SERVER=ON) |
| 产物 | libmariadb.so | libperconaserverclient.so |
| Boost 依赖 | 无 | boost/1.90.0 (Conan header-only) |
| OpenSSL | openssl/3.0.13 | openssl/1.1.1w |

## 依赖版本
- OpenSSL: 1.1.1w (Conan)
- zlib: 1.3.1 (Conan)
- Boost: 1.90.0 (Conan header-only, 替代 CMake DOWNLOAD_BOOST)

## 注意事项
- percona-server 源码包很大 (~455MB)，CI 下载需要较长时间
- 使用 Conan boost head-only 包替代 CMake DOWNLOAD_BOOST，避免构建时网络下载
- 通过 OPENSSL_ROOT_DIR / ZLIB_ROOT 显式指定依赖路径，避免 CMake find 失败
- 仅构建 mysqlclient 目标，不会触发完整的 MySQL 测试套件
- 被 qt-percona-server 作为 QMYSQL 驱动后端依赖使用
- 产物库名为 libperconaserverclient（区别于 MySQL 的 libmysqlclient 和 MariaDB 的 libmariadb）

## 交付物
| 文件 | 说明 |
|------|------|
| libperconaserverclient.so | 动态链接客户端库 |
| libperconaserverclient.a | 静态链接客户端库 |
| include/mysql.h | MySQL C API 头文件 |

**编译结束**: 2026-07-19
**最终状态**: built