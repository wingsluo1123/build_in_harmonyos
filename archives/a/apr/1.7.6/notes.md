# apr 1.7.6 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-08-09
- 编译器: clang/clang++
- 状态: published (conan create 验证通过)

## 编译步骤

1. 下载源码: https://dlcdn.apache.org/apr/apr-1.7.6.tar.gz
2. 应用补丁:
   - 0001-config.guess-ohos.patch: 添加 HarmonyOS 系统检测和 __OHOS__ LIBC=ohos
   - 0002-configure-umask.patch: 修复 umask 077 → 022 解决 HMDFS 权限问题
3. configure: ./configure --disable-shared --enable-static --prefix=...
4. make -j1
5. make install

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | UNAME_SYSTEM="HarmonyOS" 不在 Linux\|GNU case 中 | 添加 HarmonyOS case，直接设置 LIBC=ohos，跳过编译检测 |
| 2 | aarch64:HarmonyOS 未匹配 GUESS | 第二 case 语句缺少 HarmonyOS 模式 | 添加 aarch64:HarmonyOS:*:* case，设置 GUESS=$UNAME_MACHINE-unknown-linux-$LIBC |
| 3 | configure umask 077 权限问题 | HMDFS 文件系统限制 | sed 替换 umask 077 → umask 022 |

## 源码修改

- 0001-config.guess-ohos.patch: build/config.guess 添加 HarmonyOS 检测
- 0002-configure-umask.patch: configure 修复 umask

## 依赖版本

- 无外部依赖

## 验证结果

```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# 结果: 成功，测试通过 (1/1 test passed)

test output:
apr version: 1.7.6.0
test apr 1.7.6: OK
```

## 注意事项

- config.guess 需要 HarmonyOS 直接检测（不依赖编译检测），因为 HarmonyOS 上编译临时文件可能有权限问题
- conanfile.py 使用 AutotoolsToolchain，库文件名为 apr-1 (libapr-1.a)
- 默认静态链接 (shared=False)

**编译结束**: 2026-08-09
**最终状态**: published
---

**编译结束**: 2026-08-09 04:20
**最终状态**: built
