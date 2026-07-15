# stuntman 1.2.17 适配笔记

## 编译环境
- 构建系统: makefile（自定义 Makefile + common.inc，非 autotools/cmake）
- 编译日期: 2026-07-15
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: built

## 源码信息
- 下载 URL: https://github.com/jselbie/stunserver/archive/refs/heads/master.tar.gz
- 版本: 1.2.17 (June 30, 2024)
- 官方网站: https://www.stunprotocol.org/
- GitHub: https://github.com/jselbie/stunserver

## 依赖

| 依赖 | 版本 | 来源 | 说明 |
|------|------|------|------|
| openssl | 3.5.6 | ohpcd 制品仓 | 提供 libcrypto (STUN 消息完整性验证) |
| boost | 1.72.0 | SourceForge 下载 | header-only (shared_ptr, property_tree, crc) |

### Boost 说明
- Boost 不在 ohpcd 制品仓，conanfile.py build() 方法中从 SourceForge 下载 1.72.0 源码
- 必须使用 1.72.0，不能使用 1.83+（1.83 使用 pthread_setcancelstate，OHOS 不支持）
- 仅需 header-only，无需编译 Boost 库

## 编译步骤

1. 下载源码包: `https://github.com/jselbie/stunserver/archive/refs/heads/master.tar.gz`
2. 下载 Boost 1.72.0 源码（header-only）
3. 修改 `common.inc`:
   - 设置 `BOOST_INCLUDE` 指向 Boost headers
   - 设置 `OPENSSL_INCLUDE` 指向 OpenSSL headers
   - 添加 `LDFLAGS` 使用 GNU ld 并添加库搜索路径
4. `make -j1`（编译静态库 + 三个二进制）
5. 手动安装二进制到 bin/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lld 链接器无法执行 | OHOS SDK 的 lld 依赖 libxml2.so.16，系统不可用 | 使用 GNU ld (/data/service/hnp/bin/ld) 替代 |
| 2 | Boost 头文件缺失 | 系统未安装 Boost | 下载 Boost 1.72.0 源码，提取 headers |
| 3 | Boost 1.83 编译失败 | pthread_setcancelstate 未在 OHOS 实现 | 使用 Boost 1.72.0（不含此 API） |
| 4 | 没有 make install 目标 | 自定义 Makefile 无 install 目标 | 手动复制二进制 |
| 5 | OpenSSL 3.x 弃用警告 | MD5/HMAC API 在 OpenSSL 3.0 标记弃用 | 仅警告，不影响编译和运行 |

## 源码修改

所有修改通过 conanfile.py build() 方法中的 replace_in_file 动态完成：
- `common.inc`: 设置 BOOST_INCLUDE、OPENSSL_INCLUDE、添加 LDFLAGS
- 无静态补丁文件（路径依赖 Conan 依赖解析结果）

## 产物

| 文件 | 说明 |
|------|------|
| stunserver | STUN 服务端二进制 |
| stunclient | STUN 客户端二进制 |
| stuntestcode | 单元测试二进制（13 个测试套件） |

## 验证结果

```bash
# 编译验证: make -j1 → 成功
# 产物检查: stunserver, stunclient, stuntestcode → 3 个 ELF 二进制
# 单元测试: stuntestcode（需 ELF 签名后才能在 OHOS 上执行）
```

## 注意事项

- stuntman 使用自定义 Makefile，没有 configure 和 install 目标
- lld 链接器在 OHOS 上不可用（依赖 libxml2.so.16），必须使用 GNU ld
- Boost 1.72.0 必须从 SourceForge 下载（不在 ohpcd 制品仓）
- stunserver/stunclient 没有 --version 选项，只有 --help
- 二进制需要 ELF 签名才能在 HMDFS 上执行
---

**编译结束**: 2026-07-15 18:09
**最终状态**: built
