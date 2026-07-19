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
  -DDOWNLOAD_BOOST=1 \
  -DDOWNLOAD_BOOST_TIMEOUT=28800 \
  -DCMAKE_POSITION_INDEPENDENT_CODE=ON
```

### 编译
```bash
cmake --build build --target mysqlclient
```

### 安装产物
```bash
# 手动复制到 Conan package folder
cp build/libmysqlclient/libperconaserverclient.* <package>/lib/
cp -r include/* <package>/include/
cp build/include/*.h <package>/include/mysql/
```

## 与同类配方对比
| 项目 | mariadb-connector-c | percona-server |
|------|---------------------|----------------|
| 源码大小 | ~8 MB | ~455 MB |
| 构建范围 | 完整客户端库 | 仅客户端库 (WITHOUT_SERVER=ON) |
| 产物 | libmariadb.so | libperconaserverclient.so |
| 协议兼容 | MySQL 协议 | MySQL 协议 |
| 额外依赖 | 无 | Boost 头文件(自动下载) |

## 依赖版本
- OpenSSL: 1.1.1w
- zlib: 1.3.1
- Boost: 自动下载 (CMake DOWNLOAD_BOOST=1)

## 注意事项
- percona-server 源码包很大 (~455MB)，CI 下载需要较长时间
- Boost 头文件由 CMake 自动下载，超时设为 8 小时 (28800 秒)
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
