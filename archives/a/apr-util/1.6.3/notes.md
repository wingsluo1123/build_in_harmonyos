# apr-util 1.6.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-09
- 编译器: clang/clang++
- 状态: published (conan create 验证通过)

## 编译步骤
1. 下载源码: https://archive.apache.org/dist/apr/apr-util-1.6.3.tar.gz
2. 应用补丁: config.guess HarmonyOS, configure umask, config.sub ohos-linux
3. configure: --disable-shared --enable-static --with-apr=... --with-expat=...
4. make -j1
5. make install

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS | UNAME_SYSTEM 不在 Linux case | 添加 HarmonyOS case，设置 LIBC=ohos |
| 2 | config.sub 不识别 ohos | 旧版 config.sub 缺少 ohos 支持 | 添加 ohos* / ohos-linux / linux-ohos* |
| 3 | configure umask 077 权限 | HMDFS 限制 | umask 077 → 022 |
| 4 | apr_rules.mk 路径错误 | APR DESTDIR 安装后 prefix=/ | 在 APR package() 修复 apr-1-config 和 apr_rules.mk |

## 依赖版本
- apr/1.7.6 (本地构建)
- expat/2.8.2 (制品仓)

## 验证结果
conan create: PASSED, 1/1 test passed

**编译结束**: 2026-08-09
**最终状态**: published
