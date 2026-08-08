# xmlrpc-c 1.64.03 适配笔记

## 编译环境
- 构建系统: autotools (custom configure + GNUmakefile)
- 编译日期: 2026-08-09
- 编译器: clang 15.0.4 / clang++
- 状态: published

## 编译步骤

```bash
# 1. 设置 curl 和 openssl 环境 (from conan ohpcd repo)
# curl/8.15.0 and openssl/3.5.6.1 installed via conan

# 2. 创建 wrapper curl-config (conan recipe handles this in generate())

# 3. 创建 openssl.pc for pkg-config detection

# 4. Apply patches and configure
./configure --prefix=$DEFAULT_PREFIX
make -j2
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | HMDFS umask 077 导致临时目录创建失败 | E011 | 补丁修改 umask 077→022 (config.guess + configure) |
| 2 | config.guess 不识别 HarmonyOS | E007 | 补丁添加 HarmonyOS 检测分支 |
| 3 | 无 curl 开发文件，客户端库无法构建 | 系统无 curl-dev | 使用 conan ohpcd 仓的 curl/8.15.0，生成 wrapper curl-config |
| 4 | 无 openssl 开发文件，abyss-openssl 无法构建 | 系统无 openssl-dev | 使用 conan ohpcd 仓的 openssl/3.5.6.1，生成 openssl.pc |

## 源码修改

- 0001-config.guess.patch: 添加 HarmonyOS 平台检测 + umask 修复
- 0002-configure.patch: configure 中 umask 修复

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| curl | 8.15.0 | conan ohpcd 制品仓 |
| openssl | 3.5.6.1 | conan ohpcd 制品仓 (curl 的传递依赖) |

## 构建特性

```
xmlrpc-c-config --features: c++ abyss-server curl-client
```

## 验证结果

```bash
xmlrpc-c-config --version → 1.64.3
xmlrpc-c-config --features → c++ abyss-server curl-client
```

## 产物

- 核心库: libxmlrpc.a/so, libxmlrpc_util.a/so
- 客户端: libxmlrpc_client.a/so (curl transport), libxmlrpc_client++.a/so
- 服务端: libxmlrpc_server.a/so, libxmlrpc_server_abyss.a/so, libxmlrpc_server_cgi.a/so
- Abyss: libxmlrpc_abyss.a/so, libxmlrpc_openssl.a/so
- XML 解析: libxmlrpc_xmlparse.a/so, libxmlrpc_xmltok.a/so (bundled expat)
- C++ 包装: libxmlrpc++.a/so, libxmlrpc_cpp.a/so, 等
- 工具: xmlrpc-c-config

## 注意事项

- C++ 测试套件 (test/cpp/server_abyss.cpp) 存在 std::bind/POSIX bind 冲突，主库编译正常
- xmlrpc-c 内置 expat，无需外部 libxml2 依赖
---

**编译结束**: 2026-08-09 02:57
**最终状态**: built
