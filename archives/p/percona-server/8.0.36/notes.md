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
  -DDOWNLOAD_BOOST=0 \
  -DWITH_AUTHENTICATION_LDAP=OFF \
  -DWITHOUT_COMPONENT_KEYRING_KMIP=ON \
  -DWITH_EDITLINE=system \
  -DOPENSSL_ROOT_DIR=<openssl-package>/ \
  -DZLIB_ROOT=<zlib-package>/ \
  -DCMAKE_POSITION_INDEPENDENT_CODE=ON
```

### 编译
```bash
cmake --build build --target perconaserverclient -- -j1
```

## 与同类配方对比
| 项目 | mariadb-connector-c | percona-server |
|------|---------------------|----------------|
| 源码大小 | ~8 MB | ~455 MB |
| 构建范围 | 完整客户端库 | 仅客户端库 (WITHOUT_SERVER=ON) |
| 产物 | libmariadb.so | libperconaserverclient.so |
| Boost 依赖 | 无 | 预取 Boost 1.77.0 头文件 |
| OpenSSL | openssl/3.0.13 | openssl/3.5.6 |

## 依赖版本
- OpenSSL: 3.5.6 (Conan)
- zlib: 1.3.1 (Conan)
- Boost: 1.77.0 头文件（archives.boost.io，适配时预取）

## 注意事项
- `source()` 中对上游 CMake 做最小定点调整：client-only 构建缺失 editline/curses 时降为 warning，缺失 DNS SRV resolver API 时提供 unsupported stub，并在 OHOS 上将缺失的 pthread_cancel 包装为 no-op，并修正 get_password.cc 中 my_read 的 uchar 缓冲区类型。
- percona-server 源码包很大 (~455MB)，CI 下载需要较长时间
- 预取 Boost 1.77.0 头文件，避免上游 JFrog 下载地址返回非归档内容导致 CMake 解包失败
- 通过 OPENSSL_ROOT_DIR / ZLIB_ROOT 显式指定依赖路径，避免 CMake find 失败
- 仅构建 perconaserverclient 目标，关闭 LDAP/SASL/Kerberos 可选认证插件，并允许 client-only 构建在缺少 editline/curses、DNS SRV resolver API 时继续
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