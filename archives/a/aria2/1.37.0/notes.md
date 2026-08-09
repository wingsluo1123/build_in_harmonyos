# aria2 1.37.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-09
- 编译器: clang/clang++
- 状态: built

## 编译步骤
1. init-build 下载源码 (aria2-1.37.0.tar.gz, sha256: 8e7021c6...)
2. conan install 安装依赖 (openssl, c-ares, expat, zlib, sqlite3, gmp, libxml2, libuv, cppunit)
3. 从源码编译 libssh2 1.11.1 (不在制品仓中)
4. patch config.guess/config.sub 支持 OHOS 平台
5. patch configure 移除 umask 077 (HMDFS 权限问题)
6. ./configure --prefix=... --with-libuv --without-gnutls
7. make -j1 (HMDFS 不支持 mkfifo for jobserver)
8. make install DESTDIR
9. make check: 980/982 tests passed (2 failures: RC4 cipher - OpenSSL legacy provider)

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 旧版 config.guess 无 OHOS 分支 | patch-autotools-ohos.pl + 手动修复 config.sub linux-ohos |
| 2 | config.status Permission denied | umask 077 + HMDFS SGID bit 冲突 | 移除 configure/config.status 中的 umask 077 |
| 3 | deps/wslay/configure 无法识别平台 | 子项目 wslay 也有独立 config.guess | 对 wslay 同样打补丁 |
| 4 | make -j2 jobserver 失败 | HMDFS 不支持 mkfifo | 使用 make -j1 |
| 5 | libssh2 不在制品仓 | 制品仓无 libssh2 包 | 从源码编译 libssh2 1.11.1 (OpenSSL backend) |
| 6 | 2 个测试失败 (RC4 cipher) | OpenSSL 3.x legacy provider 未安装 | 平台限制，不阻塞 |
| 7 | lld 需要 libxml2.so.16 | 系统工具链依赖 | 设置 LD_LIBRARY_PATH 包含 OHOS SDK lib |

## 注意事项
- libssh2 不在 conan 制品仓中，conan 构建时 SFTP 功能不可用
- 需要先适配并发布 libssh2 conan 包才能在 conan 构建中启用 SFTP
- RC4 算法不可用 (OpenSSL legacy provider 缺失)，影响 2 个测试
---

**编译结束**: 2026-08-10 02:33
**最终状态**: built
