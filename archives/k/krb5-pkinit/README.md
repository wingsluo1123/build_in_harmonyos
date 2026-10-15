# krb5-pkinit

MIT Kerberos 5 PKINIT 支持包（对应 Linux 发行版 krb5-pkinit 拆分，
提供基于证书的初始认证：客户端 clpreauth 插件 + KDC kdcpreauth 插件）。

## 适配说明（1.22.2）

- 源码为官方 MIT Kerberos 5 `krb5-1.22.2.tar.gz`（web.mit.edu），
  Autotools 构建，源码在 `src/` 子目录（配方中提升到根目录）。
- 复用 krb5 1.22.2 的 4 个鸿蒙适配 patch（config.guess/config.sub/umask/dnsglue）
  + 新增 0005 LibreSSL 兼容 patch。
- 依赖 openssl（`--with-system-openssl` + `--enable-pkinit`）。
- install 服务端组件（同 krb5-server）：sbin 二进制 + 库集 + 头 +
  `lib/krb5/plugins/preauth/pkinit.so`（PKINIT 客户端与 KDC 插件）。

## 关键适配点

1. **openssl 依赖路径显式传递**：conan 的 AutotoolsToolchain 默认不把依赖的
   include/lib 注入 configure，导致 PKINIT 的 openssl 版本检测（编译 opensslv.h
   测试程序）失败而**静默禁用** PKINIT（krb5-server 即因此不含 pkinit 插件）。
   本配方在 generate() 中显式追加 openssl 的 include/lib/rpath 后检测通过。
2. **LibreSSL 兼容（0005 patch）**：ohpcd 的 openssl/3.5.8.1 实为 LibreSSL 3.9.1
   （`OPENSSL_VERSION_NUMBER` 伪装 0x20000000L，走 krb5 的 <3.0 旧 API 分支）。
   LibreSSL 无 `EVP_PKEY_DHX` / `d2i_DHxparams` / `EVP_PKEY_CTRL_DH_PAD`，
   按 `LIBRESSL_VERSION_NUMBER` 条件改用 `EVP_PKEY_DH` / `d2i_DHparams` /
   跳过 pad 设置（调用方有短结果长度调整兜底）。
3. **静态 LibreSSL**：ohpcd openssl 仅提供 libcrypto.a（静态库），pkinit.so
   将 LibreSSL 静态链入插件（自包含，无需运行时额外 .so）。

## 与 krb5-server 的关系

krb5-server（无 PKINIT）与 krb5-pkinit（--enable-pkinit）均为独立包，
各自全量构建 krb5-1.22.2，不互依赖。KDC 启用 PKINIT 时使用 krb5-pkinit 的
krb5kdc + pkinit.so 插件。
