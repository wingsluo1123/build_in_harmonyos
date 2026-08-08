# apr-util 1.6.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-09
- 编译器: clang/clang++
- 状态: published (conan create 验证通过)

## 编译步骤

1. 下载源码: https://archive.apache.org/dist/apr/apr-util-1.6.3.tar.gz
2. 应用补丁:
   - 0001-config.guess-ohos.patch: 添加 HarmonyOS 系统检测
   - 0002-configure-umask.patch: 修复 umask 077 → 022
   - 0003-config.sub-ohos.patch: 添加 ohos-linux 支持
3. configure: ./configure --disable-shared --enable-static --with-apr=... --with-expat=...
4. make -j1
5. make install

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | UNAME_SYSTEM="HarmonyOS" 不在 Linux case 中 | 添加 HarmonyOS case，直接设置 LIBC=ohos |
| 2 | config.sub 不识别 ohos OS | 旧版 config.sub 缺少 ohos 支持 | 添加 ohos* 到 OS 列表，ohos-linux 解析，linux-ohos* 到 kernel-os case |
| 3 | configure umask 077 权限问题 | HMDFS 文件系统限制 | sed 替换 umask 077 → umask 022 |
| 4 | apr_rules.mk 路径错误 | APR DESTDIR 安装后 prefix=/ 导致 apr_builddir=//build-1 | 在 APR package() 中修复 apr-1-config prefix 和 apr_rules.mk 的 apr_builddir/apr_builders/top_builddir |

## 依赖版本

- apr/1.7.6 (本地构建)
- expat/2.8.2 (制品仓)

## 验证结果

```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# 结果: 成功，测试通过 (1/1 test passed)

test output:
apr-util version: 1.6.3
APU_IS_DEV_BUILD: 0
test apr-util 1.6.3: OK
```

**编译结束**: 2026-08-09
**最终状态**: published
