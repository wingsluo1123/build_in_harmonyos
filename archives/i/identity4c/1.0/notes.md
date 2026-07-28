# identity4c 1.0 适配笔记

## 编译环境
- 构建系统: autotools (autogen.sh → configure → make)
- 编译日期: 2026-07-28
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. **init-build**: 使用 ohc-run.py init-build 下载源码
   - 源码: https://github.com/ufpidentity/identity4c
   - Tag: 1.0 (无 1.0 tag 时回退到 master)
   
2. **源码结构**: 
   - 主库源: identity.c, identity-openssl-bridge.c, identity-resolver.c, identity-xml-parser.c
   - 捆绑源: strmap.c (LGPL-3), picohttpparser.c (MIT)
   - 构建配置: configure.ac, Makefile.am, autogen.sh

3. **依赖**:
   - openssl/3.5.6 (SSL/TLS)
   - libxml2/2.15.3 (XML 解析)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | openssl/libxml2 未发布到远程 | 依赖包仅 built 未 published | conan create 会自动从源码构建依赖 |
| 2 | automake 和 libtool 在构建环境中缺失 | 环境未安装完整 autotools 工具链 | conan 构建时会使用配置好的工具链 |
| 3 | configure.ac 中 AC_SUBST 语法问题 | 缺少 shell 引用 | 添加补丁 0003-configure.ac.patch |

## 依赖版本
- openssl/3.5.6
- libxml2/2.15.3

## 交付物

| 文件 | 说明 |
|------|------|
| libufpidentity.a | 静态库 |
| libufpidentity.so | 共享库 (可选) |
| include/identity.h | 公共头文件 |
| include/strmap.h | strmap 头文件 |

## 注意事项
- 使用 AutotoolsToolchain + Autotools helper (R33 合规)
- test_package 验证 strmap API 和库链接 (R34 合规)
- 平台检查使用 `os in ("Linux", "OHOS")` (R32 合规)
---

**编译结束**: 2026-07-28 19:58
**最终状态**: built
