# checkbashisms 2.25.28 — 适配笔记

## 软件概述
checkbashisms 是一个 Perl 脚本工具，来自 Debian devscripts 包，用于检测 shell 脚本中的 bashisms（非 POSIX 兼容的 bash 特有语法）。

## 构建系统
- **类型**: Makefile（非 autotools，无 configure 脚本）
- **源码**: devscripts v2.25.28 from salsa.debian.org
- **构建过程**: 
  1. 创建 version 文件（正常由 dpkg-parsechangelog 生成，OHOS 不可用故手动创建）
  2. 从 checkbashisms.pl 生成 checkbashisms（sed 替换 ###VERSION###）
  3. 修复 shebang: #!/usr/bin/perl → #!/usr/bin/env perl
  4. 安装到 bin/ 和 share/man/man1/

## 遇到的问题

### 1. dpkg-parsechangelog 不可用
- **原因**: OHOS 平台无 dpkg 工具链
- **解决**: 手动创建 version 文件，内容为 "2.25.28"

### 2. shebang 路径不匹配
- **原因**: 脚本 shebang 为 #!/usr/bin/perl，但 OHOS perl 在 /storage/Users/currentUser/usr/local/bin/perl
- **解决**: 修改 shebang 为 #!/usr/bin/env perl
- **track-edit**: scripts/checkbashisms.pl

### 3. chmod --reference 不被支持
- **原因**: toybox chmod 不支持 --reference 参数，影响 debchange 构建
- **影响**: 不影响 checkbashisms 构建（checkbashisms 在 debchange 之前已成功构建）

### 4. po4a 工具缺失
- **原因**: po4a（翻译工具）未安装
- **影响**: translated_manpages 目标无法构建（非必需，不影响 checkbashisms 功能）

### 5. shunit2 不可用
- **原因**: shunit2 测试框架未安装
- **影响**: make check 无法自动运行测试套件
- **解决**: 手动运行 checkbashisms 测试用例验证功能

## 测试验证
手动运行了以下测试，全部通过：
- 531327.sh: 干净脚本，无 bashism 检测到，exit 0 ✅
- 808271.sh: 检测到 type bashism，exit 1 ✅
- arith.sh: 检测到算术 bashism，exit 1 ✅
- case-modification.sh: 检测到大小写修改 bashism，exit 1 ✅
- basic.mk: 检测到 Makefile 中的 echo -e bashism，exit 1 ✅

## Conan 配方
- **构建系统**: custom（非 autotools）
- **依赖**: 无
- **产物**: bin/checkbashisms（Perl 脚本）
- **license**: GPL-2.0
---

**编译结束**: 2026-07-02 17:43
**最终状态**: built
