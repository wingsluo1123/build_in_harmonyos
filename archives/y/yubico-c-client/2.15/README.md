# yubico-c-client 2.15 — OpenHarmony 预编译包

## 软件信息

- **软件名**: yubico-c-client
- **版本**: 2.15
- **描述**: Yubico YubiKey OTP 验证 C 客户端库
- **许可证**: BSD-2-Clause
- **主页**: https://github.com/Yubico/yubico-c-client
- **构建系统**: autotools (configure + make)

## 平台信息

- **目标平台**: aarch64-unknown-linux-ohos (HarmonyOS)
- **内核**: HongMeng Kernel 1.12.0
- **编译器**: clang 15.0.4
- **CFLAGS**: -fPIC -O2

## 依赖

| 依赖 | 版本 | 来源 |
|------|------|------|
| curl | 8.19.0 | 预编译包 (cmd-pkgs) |
| zlib | 1.3.1 | 预编译包 (curl 的传递依赖) |
| help2man | 1.49.3 | 预编译包 (构建工具，man 页生成) |

## 安装产物

```
$PREFIX/bin/ykclient                    # 命令行工具
$PREFIX/lib/libykclient.so.3.6.0        # 共享库
$PREFIX/lib/libykclient.so.3            -> libykclient.so.3.6.0
$PREFIX/lib/libykclient.so              -> libykclient.so.3.6.0
$PREFIX/lib/libykclient.a               # 静态库
$PREFIX/lib/libykclient.la              # libtool 归档
$PREFIX/include/ykclient.h              # 主头文件
$PREFIX/include/ykclient_errors.h       # 错误码头文件
$PREFIX/include/ykclient_server_response.h  # 服务器响应头文件
$PREFIX/include/ykclient_version.h      # 版本头文件
$PREFIX/share/man/man1/ykclient.1       # man page
```

## 构建步骤

1. 下载源码包 (GitHub tarball, tag: ykclient-2.15)
2. `autoreconf --install -f` (源码包不含生成的 configure 脚本)
3. 修补 `umask 077` → `umask 022` (HMDFS 平台权限修复)
4. `PKG_CONFIG_PATH=$PREFIX/lib/pkgconfig ./configure --prefix=$PREFIX`
5. `make -j1`
6. `make install DESTDIR=$TEST_PREFIX` (暂存验证)
7. `make check` (selftest 因网络依赖失败，见测试报告)
8. `make install` (安装到 $PREFIX)

## 补丁

| 补丁文件 | 说明 |
|----------|------|
| patches/0001-configure.patch | configure 脚本 umask 077→022 修复 (HMDFS 平台) |

## 质量验证

- **conan-verify**: G1 ✅ G0 ✅ G2 ✅ G3 ✅ G4 ✅ L2 ✅ L4 ✅ L5 ✅
- **verify-build**: G1 ✅ G2 ✅ G3 ✅ G4 ✅
- **submit**: 6/6 PASS
