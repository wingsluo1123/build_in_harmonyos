# apr 1.7.6 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-05
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: https://dlcdn.apache.org/apr/apr-1.7.6.tar.gz
2. 应用 OHOS 平台补丁:
   - patch-autotools-ohos.pl build/config.guess build/config.sub
   - sed -i 's/umask 077/umask 022/g' configure
3. ./configure --prefix=/storage/Users/currentUser/usr/local
4. make -j2
5. make install DESTDIR=$TEST_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | E007: 缺少 __OHOS__ LIBC 检测 | patch-autotools-ohos.pl 添加 HarmonyOS 系统识别 |
| 2 | config.sub 不支持 ohos-linux | E072: 缺少 ohos-linux triplet | patch-autotools-ohos.pl 添加 ohos-linux 支持 |
| 3 | config.status Permission denied | E011: HMDFS 上 umask 077 导致权限不足 | sed umask 077 → umask 022 |

## 源码修改

- 0001-build-config.guess.patch: 添加 __OHOS__ LIBC 检测和 HarmonyOS 系统识别
- 0002-build-config.sub.patch: 添加 ohos-linux triplet 支持
- 0003-configure.patch: 修复 umask 077 → 000 解决 HMDFS 权限问题

## 依赖版本

无外部依赖

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

- APR 是系统级库，默认静态链接 (R26)
- 构建产物: libapr-1.a, libapr-1.so, apr-1-config, apr-1.pc
---

**编译结束**: 2026-08-05 01:08
**最终状态**: built

