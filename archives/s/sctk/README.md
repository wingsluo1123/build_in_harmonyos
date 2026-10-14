# sctk — OpenHarmony 编译档案

## 软件简介
sctk（Speech Recognition Scoring Toolkit，NIST 语音识别评分工具包）提供语音识别系统
评测所需的命令行工具集：sclite（sclite/sc_stats/sctkUnit/rover 评分工具）、asclite
（说话人属性对齐评分）、rfilter1（GLM 规则过滤）、csrfilt / chfilt / hamzaNorm /
tanweenFilt / acomp / def_art / utf_filt（文本过滤与规范化）、hubscr（Hub 评测脚本）、
md-eval / rttmSort / rttm2ctm / rttmSmooth / spkr2sad / mergectm2rttm / align2html /
stm2rttm / stmValidator / rttmValidator / ctmValidator / slatreport（RTTM/STM/CTM 工具）。

## OHOS 适配要点
- 构建系统为纯 Makefile（顶层 makefile 驱动各子模块 makefile.in；make config 由
  sed/config.sh 生成各子模块 makefile），无 configure 脚本
- **HMDFS 临时目录**：config.sh/config.status 以 `umask 077` 在当前目录创建临时目录时，
  新目录继承父目录属主（setgid 位），当前用户非属主无法写入（E206）——补丁将临时目录
  改为 `${TMPDIR:-.}/confstatXXXXXX`
- **perl shebang**：鸿蒙无 /usr/bin/perl，perl 脚本 shebang 统一改为
  `#!/usr/bin/env perl`（18 个以补丁固化；md-eval.pl 因 CRLF 行尾无法生成补丁，
  由 conanfile.py package() 兜底统一修复）（E049）
- **/tmp 只读**：csrfilt.sh / tsclite.sh 硬编码 /tmp 改为 `${TMPDIR:-$HOME/tmp}`（E002）
- **C++ 未初始化成员**：asclite `LineStyleInputParser` 构造函数未初始化成员，在 libc++
  下读出巨大垃圾值（E632 草稿）——构造函数初始化全部成员
- **LD_LIBRARY_PATH**：conan 配方 build() 用 SDK aarch64-linux-ohos 目录干净覆盖，避免
  usr/local/lib 的 libxml2 污染 SDK lld（E266）

## 依赖关系
- 编译期：无外部库依赖
- 运行期：perl/5.42.2（perl 脚本工具必需，conan 制品仓已发布）

## 参考资料
- [SCTK 官方仓库](https://github.com/usnistgov/SCTK)