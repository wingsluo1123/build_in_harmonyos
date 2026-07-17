# texi2html 5.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-07-17
- 编译器: clang/clang++ (OHOS SDK 15.0.4)
- 目标平台: aarch64-unknown-linux-ohos
- 状态: built

## 编译步骤

```bash
# configure
./configure --build=aarch64-ohos-linux --host=aarch64-ohos-linux

# make
make -j1
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | install-sh 权限不足 (0644) | 上游 tarball 权限错误 | chmod 0755 install-sh |
| 2 | /bin/sh shebang 不兼容 | HarmonyOS 没有 /bin/sh | 替换为 /system/bin/sh |
| 3 | PACKAGE_DATE 获取失败 | mdate-sh 不兼容 OHOS | 硬编码日期 |
| 4 | umask 077 导致 mktemp 失败 | OHOS 权限限制 | 改为 umask 002 |
| 5 | Locale::Messages::dgettext 缺失 | Perl 模块未安装 | 使用 eval 安全包装 |

## 源码修改

- 0001-config.guess.patch: 更新 config.guess 支持 OHOS 检测
- 0002-config.sub.patch: 更新 config.sub 支持 OHOS triplet
- 0003-configure.patch: 修复 configure 脚本兼容性

## 验证结果

```bash
texi2html --no-validate sample.texi
# 生成 sample.html
```

## 注意事项

- 需要 Perl 运行时环境
- 依赖 libintl-perl 和 Unicode-EastAsianWidth 模块（已打包）
- 远程 CI 的 conan-build-test 可能因环境差异失败
---

**编译结束**: 2026-07-17 20:58
**最终状态**: built
