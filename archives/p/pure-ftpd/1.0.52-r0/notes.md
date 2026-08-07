# pure-ftpd 1.0.52-r0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-08
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: https://download.pureftpd.org/pub/pure-ftpd/releases/pure-ftpd-1.0.52.tar.gz
2. 应用补丁:
   - 0001-config.guess.patch: OHOS 平台检测
   - 0002-config.sub.patch: OHOS 平台检测
   - 0003-ftpd.h-statvfs64-ohos.patch: 修复 statvfs64 false positive
   - 0004-configure-mktemp-umask.patch: 修复 mktemp 权限问题
3. 通过 conan 安装 OpenSSL: conan install --requires=openssl/1.1.1w
4. 运行 configure: ./configure --prefix=$PREFIX --with-everything --with-tls ... CPPFLAGS="-I<openssl>/include" LDFLAGS="-L<openssl>/lib" LIBS="-lssl -lcrypto"
5. make -j2
6. make install DESTDIR=$TEST_PREFIX
7. make check (通过，无测试用例)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status: could not setup config files machinery | mktemp 在 OHOS 上创建的目录属主为 20001006，umask 077 导致当前用户无法写入 | 修改 configure 中 config.status 模板的 umask 077 为 022 |
| 2 | ftpd.c: error: variable has incomplete type 'struct statvfs64' | OHOS 上 struct statvfs64 只有 forward declaration，configure 检测为 false positive | 在 ftpd.h 中用 __OHOS__ 守卫，回退到 struct statvfs |

## 源码修改

- config.guess: 添加 aarch64:HarmonyOS 平台检测
- config.sub: 添加 ohos-linux 和 ohos* 平台支持
- src/ftpd.h: 添加 __OHOS__ 守卫，不使用 struct statvfs64
- configure: 修改 config.status 模板中 mktemp/mkdir 的 umask 077 为 022

## 依赖版本

- openssl/1.1.1w (conan 制品仓)

## 验证结果

```bash
$ pure-ftpd --help
# 显示所有命令行选项，确认二进制可执行
```

## 交付物

| 文件 | 说明 |
|------|------|
| sbin/pure-ftpd | FTP 服务器主程序 (2.7MB) |
| sbin/pure-ftpwho | 在线用户查看工具 |
| sbin/pure-authd | 外部认证守护进程 |
| sbin/pure-certd | TLS 证书管理守护进程 |
| sbin/pure-mrtginfo | MRTG 统计信息工具 |
| sbin/pure-quotacheck | 配额检查工具 |
| sbin/pure-uploadscript | 上传脚本执行器 |
| bin/pure-pw | 虚拟用户管理工具 |
| bin/pure-pwconvert | 密码转换工具 |
| bin/pure-statsdecode | 日志解析工具 |

## 注意事项

- pure-ftpd 是命令行工具（FTP daemon），需要声明 commands.json (R38)
- 构建依赖 OpenSSL 静态库（来自 conan 制品仓）
- 不可裁剪功能，使用 --with-everything 和全部 --with-* 选项
---

**编译结束**: 2026-08-08 03:24
**最终状态**: built
