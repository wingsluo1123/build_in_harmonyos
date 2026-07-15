# colordiff 1.0.21 适配笔记

## 编译环境
- 构建系统: makefile（纯 Perl 脚本，无 configure）
- 编译日期: 2026-07-15
- 编译器: 无需编译（Perl 脚本）
- Perl 版本: v5.42.0
- 状态: built

## 编译步骤

colordiff 是纯 Perl 脚本，无需 configure 和编译步骤：

```bash
# 1. 初始化编译环境
python3 $SKILL_ROOT/scripts/ohc-run.py init-build colordiff 1.0.21 --url=https://www.colordiff.org/colordiff-1.0.21.tar.gz

# 2. 修复 shebang（Perl 不在 /usr/bin/perl）
source .build-context-colordiff-1.0.21
cd $BUILD_SRC_DIR
sed -i '1s|#!/usr/bin/perl|#!/usr/bin/env perl|' colordiff.pl

# 3. 安装到 staging 目录
make install DESTDIR=$TEST_PREFIX INSTALL_DIR=$DEFAULT_PREFIX/bin MAN_DIR=$DEFAULT_PREFIX/share/man/man1 ETC_DIR=$DEFAULT_PREFIX/etc

# 4. 验证
$TEST_PREFIX$DEFAULT_PREFIX/bin/colordiff --version
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Perl shebang `/usr/bin/perl` 不存在 | HarmonyOS Perl 安装在 /data/service/hnp/bin/perl | 修改 shebang 为 `#!/usr/bin/env perl`，增加可移植性 |
| 2 | conan-init 生成的模板基于 autotools | colordiff 无 configure 脚本，是纯 makefile 安装 | 手动重写 conanfile.py 为 makefile install-only 模式 |

## 源码修改

### 0001-colordiff.pl.patch

修改 Perl shebang 以增加跨平台可移植性：

```diff
--- a/colordiff.pl
+++ b/colordiff.pl
@@ -1,4 +1,4 @@
-#!/usr/bin/perl
+#!/usr/bin/env perl
```

**修改原因**: HarmonyOS 的 Perl 安装在 `/data/service/hnp/bin/perl`，使用 `#!/usr/bin/env perl` 可自动定位 Perl 解释器。

## 依赖版本

- Perl: v5.42.0 (系统自带)
- diffutils: 3.10 (colordiff 的运行依赖)
- 无编译依赖

## 验证结果

```bash
$ colordiff --version
colordiff 1.0.21 (http://www.colordiff.org/)
(C)2002-2022 Dave Ewart, davee@sungate.co.uk

diff (GNU diffutils) 3.10
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/colordiff | 主 Perl 脚本（已修复 shebang） |
| bin/cdiff | cdiff.sh 包装脚本 |
| share/man/man1/colordiff.1 | 手册页 |
| share/man/man1/cdiff.1 | 手册页 |
| etc/colordiffrc | 默认配置文件 |

## 注意事项

1. colordiff 是纯 Perl 脚本，无需编译，只需安装
2. 需要 Perl 和 diffutils 作为运行依赖
3. 配置文件 colordiffrc 安装到 `$PREFIX/etc/colordiffrc`，用户可复制到 `~/.colordiffrc` 自定义颜色方案
4. 默认配置适合深色背景，浅色背景用户应使用 colordiffrc-lightbg
---

**编译结束**: 2026-07-15 16:34
**最终状态**: built
