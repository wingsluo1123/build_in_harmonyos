# colordiff 1.0.22 适配笔记

## 编译环境
- 构建系统: makefile（纯 Perl 脚本，无 configure）
- 编译日期: 2026-07-15
- 编译器: 无需编译（Perl 脚本）
- Perl 版本: v5.42.0
- 状态: built

## 编译步骤

colordiff 是纯 Perl 脚本，无需 configure 和编译步骤：

```bash
# 1. 下载源码
# URL: https://www.colordiff.org/colordiff-1.0.22.tar.gz
# SHA256: f96f73c54521c53f14dc164d5a3920c9ca21a0e5f8e9613f43812a98af3e22af

# 2. 应用补丁（修复 shebang）
patch -p1 < patches/0001-colordiff.pl.patch

# 3. 安装到 staging 目录
make install DESTDIR=$TEST_PREFIX \
  INSTALL_DIR=$DEFAULT_PREFIX/bin \
  MAN_DIR=$DEFAULT_PREFIX/share/man/man1 \
  ETC_DIR=$DEFAULT_PREFIX/etc
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Perl shebang `/usr/bin/perl` 不存在 | HarmonyOS Perl 在 `/data/service/hnp/bin/perl` | 修改 shebang 为 `#!/usr/bin/env perl`，增加可移植性 |

## 源码修改

### 0001-colordiff.pl.patch

修改 Perl shebang 以增加跨平台可移植性：

```diff
--- a/colordiff.pl
+++ b/colordiff.pl
-#!/usr/bin/perl
+#!/usr/bin/env perl
```

**修改原因**: HarmonyOS 的 Perl 安装在 `/data/service/hnp/bin/perl`，使用 `#!/usr/bin/env perl` 可自动定位 Perl 解释器。

## 依赖版本

- Perl: v5.42.0 (system)
- diffutils: 系统自带（colordiff 的运行依赖）
- 无编译依赖

## 验证结果

```bash
$ colordiff --version
diff (GNU diffutils) 3.12
# colordiff 是 diff 的包装脚本，显示 diff 版本表示运行正常
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/colordiff | Perl 脚本（diff 颜色化包装器） |
| bin/cdiff | Shell 脚本（diff 分页器包装器） |
| etc/colordiffrc | 默认颜色配置文件 |
| share/man/man1/colordiff.1 | 手册页 |
| share/man/man1/cdiff.1 | 手册页 |

## 注意事项

1. colordiff 是纯 Perl 脚本，无需编译，只需安装
2. 需要 Perl 和 diffutils 作为运行依赖
3. 配置文件 colordiffrc 安装到 `$PREFIX/etc/colordiffrc`，用户可复制到 `~/.colordiffrc` 自定义颜色方案
4. 默认配置适合深色背景，浅色背景用户应使用 colordiffrc-lightbg
---

**编译结束**: 2026-07-15 15:49
**最终状态**: built
