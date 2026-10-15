# krb5-server

MIT Kerberos 5 服务端组件（独立包，对应 Linux 发行版 krb5-server 拆分）。

## 适配说明（1.22.2）

- 源码为官方 MIT Kerberos 5 `krb5-1.22.2.tar.gz`（web.mit.edu），
  Autotools 构建，源码在 `src/` 子目录（配方中提升到根目录）。
- 复用 krb5 1.22.2 的 4 个鸿蒙适配 patch：
  - config.guess/config.sub：添加 HarmonyOS / ohos-linux triplet 识别
  - configure：umask 077→000（E082：HarmonyOS umask+SGID 临时目录不可写）
  - dnsglue.c：musl libc 无 `_res` 全局变量，PRIMARY_DOMAIN 返回 NULL
- 依赖 openssl（`--with-system-openssl`），KDC/PKINIT 需要系统 OpenSSL。
- install 服务端组件：sbin 二进制（krb5kdc/kadmind/kdb5_util/kpropd）+
  服务端库（kadm5srv_mit/kdb5/krad）与运行时依赖的 krb5 库集 + 头文件。
- test_package：链接服务端库集（krb5_init_context）+ 真实调用 kdb5_util
  创建/查询临时 KDB（断言 K/M@TEST.REALM principal 存在）。

## 与 krb5（客户端库包）的关系

ohpcd 已发布 krb5/1.22.1（客户端库 + 全量工具）。krb5-server 为 1.22.2
服务端独立包，自包含构建（不依赖 krb5 包），两者无共享二进制依赖。
