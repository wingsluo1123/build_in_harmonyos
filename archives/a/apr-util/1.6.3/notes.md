# apr-util 1.6.3 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-05
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: https://dlcdn.apache.org/apr/apr-util-1.6.3.tar.gz
2. 应用 OHOS 平台补丁:
   - patch-autotools-ohos.pl build/config.guess build/config.sub
   - 手动添加 linux-ohos* 到 config.sub kernel-OS 列表
   - sed -i 's/umask 077/umask 022/g' configure
3. ./configure --prefix=... --with-apr=... --with-expat=...
4. make -j2
5. make install DESTDIR=$TEST_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 不识别 HarmonyOS | E007: 缺少 HarmonyOS 系统检测 | patch-autotools-ohos.pl |
| 2 | config.sub 拒绝 linux-ohos | 缺少 linux-ohos* kernel-OS 兼容性 | 手动添加 linux-ohos* 到 case 列表 |
| 3 | config.status Permission denied | E011: HMDFS umask 077 权限不足 | sed umask 077→022 |
| 4 | apr_rules.mk 中 apr_builddir=//build-1 | APR 构建时 --prefix=/ 导致 | 修复 apr_rules.mk 中的 apr_builddir 路径 |

## 源码修改

- 0001-build-config.guess.patch: 添加 HarmonyOS 系统识别
- 0002-build-config.sub.patch: 添加 ohos-linux 和 linux-ohos* 支持
- 0003-configure.patch: 修复 umask 077→022

## 依赖版本

- apr/1.7.6 (conan cache)
- expat/2.8.2 (artifact repo)

## 验证结果

```bash
# conan-verify 所有门禁通过
G1 (recipe completeness): PASS
G2 (conan create clean build): PASS
G3 (system library isolation): PASS
G4 (product completeness): PASS
L2 (smoke test): PASS
L4 (security scan): PASS
L5 (baseline): PASS
W3 (local CI simulation): PASS
```

## 注意事项

- apr-1-config 和 apr_rules.mk 需要在 build() 中修复路径
- test_package 使用 AutotoolsDeps 而非 CMakeDeps 以正确解析依赖路径
---

**编译结束**: 2026-08-05 03:05
**最终状态**: built
