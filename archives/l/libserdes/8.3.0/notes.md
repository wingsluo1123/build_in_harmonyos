# libserdes 8.3.0 适配笔记

## 编译环境
- 构建系统: mklove (custom autotools-like configure + make)
- 编译日期: 2026-07-06
- 编译器: clang 15.0.4 / clang++
- 状态: published

## 编译步骤

```bash
source .build-context-libserdes-8.3.0
cd $BUILD_SRC_DIR
./configure --prefix=$DEFAULT_PREFIX
make -j2
make install DESTDIR=$TEST_PREFIX
make install
make check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败，无法下载源码 | 系统SSL证书路径不匹配 | 设置 SSL_CERT_FILE=/storage/Users/currentUser/usr/local/ssl/cert.pem |
| 2 | avro-c依赖缺失，无预编译包 | avro-c不在cmd-pkgs和Conan制品仓中 | 从GitHub下载Apache Avro 1.11.3源码，手动编译安装avro-c |
| 3 | avro-c CMake版本检测失败 | CMake 4.1.2不兼容avro-c的cmake_minimum_required(3.1) | 添加-DCMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 4 | avro-c version.sh执行失败导致CMake配置错误 | CMake execute_process无法在HarmonyOS上执行bash脚本 | 在CMakeLists.txt中硬编码版本变量作为fallback |
| 5 | jansson缺失 | 无预编译包安装 | 从cmd-pkgs安装jansson 2.15.0预编译包 |
| 6 | CI门禁失败: configure找不到jansson/curl/avro-c | conanfile.py的requirements()为空，build()硬编码~/usr/local路径，CI worker无预装依赖 | 修复conanfile.py: 声明requirements()引用@ohpcd/stable, 使用VirtualBuildEnv管理依赖路径 |

## 依赖版本

| 依赖 | 版本 | 来源 | Conan引用 |
|------|------|------|-----------|
| jansson | 2.15.0 | cmd-pkgs预编译包 | jansson/2.15.0@ohpcd/stable |
| libcurl | 8.19.0 | 系统预装 | curl/8.19.0@ohpcd/stable |
| avro-c | 1.11.3 | 手动编译(Apache Avro release-1.11.3) | avro-c/1.11.3@ohpcd/stable |
| libpthread | system | 系统库 | (system_libs) |
| librt | system | 系统库 | (system_libs) |

## ⚠️ CI依赖链状态

conanfile.py 已声明以下 Conan 依赖:
- `jansson/2.15.0@ohpcd/stable`
- `curl/8.19.0@ohpcd/stable`
- `avro-c/1.11.3@ohpcd/stable`

**这三个依赖尚未适配/发布到 @ohpcd/stable 制品仓。** CI `conan create` 将在依赖解析阶段失败，报错 "Missing recipe"。

**解决方案**: 先适配并发布以上三个依赖包到 @ohpcd/stable，然后 libserdes 的 CI 即可通过。

## 验证结果

```
make check:
libserdes.so.1                 OK
libserdes.a                    OK
```

## 注意事项

- libserdes使用mklove构建系统（非标准autotools），configure脚本位于源码根目录
- avro-c是必需依赖（configure中标记为fail），不可禁用
- avro-cpp和librdkafka是可选依赖，已禁用
- 构建产物：libserdes.so.1（共享库）+ libserdes.a（静态库）
- pkg-config名称为serdes（非libserdes），链接使用-lserdes
- conanfile.py使用VirtualBuildEnv管理依赖路径（不硬编码~/usr/local）
- conanfile.py build()方法包含make check（CI L1c合规）
---

**编译结束**: 2026-07-06 12:34
**CI修复**: 2026-07-07
**最终状态**: published (CI pending — 等待依赖发布)
